import collections
import contextlib
import functools
import importlib
import keyword
import os
import string
import tempfile

import gin
import hypothesis
from hypothesis import strategies as st

from hyperion import ast
from hyperion import parsing
from hyperion import rendering
from hyperion import transforms


global_max_size = 2


def unary_operators(safe):
    if safe:
        operators = ast.safe_unary_operators
    else:
        operators = ast.unary_operators
    return st.one_of(*map(st.just, operators))


def binary_operators(safe):
    if safe:
        operators = ast.safe_binary_operators
    else:
        operators = ast.binary_operators
    return st.one_of(*map(st.just, operators))


@st.composite
def strings(draw):
    string_st = st.text(
        alphabet=st.characters(blacklist_categories=("C", "Zl", "Zp")),
        max_size=global_max_size,
    )
    return ast.String(draw(string_st))


@st.composite
def names(draw):
    keywords = set(keyword.kwlist) | {"product", "union", "table"}

    name = None
    while name in keywords or name is None:

        def chars(char_set):
            return st.characters(
                whitelist_categories=(),
                whitelist_characters=nondigits,
            )

        nondigits = string.ascii_letters + "_"
        first = draw(chars(nondigits))
        rest = draw(
            st.text(
                alphabet=chars(nondigits + string.digits),
                max_size=(global_max_size - 1),
            )
        )
        name = first + rest

    return name


@st.composite
def macros(draw):
    return ast.Macro(name=draw(names()))


def internal_lists(item_st, allow_empty=True, **kwargs):
    list_kwargs = {"max_size": global_max_size}
    if not allow_empty:
        list_kwargs["min_size"] = 1
    list_kwargs.update(kwargs)
    return st.lists(item_st, **list_kwargs)


@st.composite
def scopes(draw):
    return ast.Scope(path=tuple(draw(internal_lists(names()))))


@st.composite
def namespaces(draw, min_size=1, max_size=global_max_size):
    path_st = internal_lists(names(), min_size=min_size, max_size=max_size)
    return ast.Namespace(path=tuple(draw(path_st)))


@st.composite
def identifiers(draw, with_module=False, flat=False):
    if flat:
        scope = ast.Scope(path=())
    else:
        scope = draw(scopes())
    min_size = 2 if with_module else 1
    max_size = min_size if flat else global_max_size
    return ast.Identifier(
        scope=scope,
        namespace=draw(namespaces(min_size=min_size, max_size=max_size)),
        name=draw(names()),
    )


@st.composite
def references(draw):
    return ast.Reference(identifier=draw(identifiers()))


def expr_base(for_eval):
    base_sts = [
        st.booleans(),
        st.integers(min_value=0, max_value=10),
        st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    ]
    if not for_eval:
        base_sts += [
            st.none(),
            strings(),
            macros(),
            references(),
        ]
    return st.one_of(*base_sts)


@st.composite
def dicts(draw, expr_st):
    items_st = internal_lists(st.tuples(expr_st, expr_st))
    return ast.Dict(items=tuple(draw(items_st)))


@st.composite
def lists(draw, expr_st):
    items_st = internal_lists(expr_st)
    return ast.List(items=tuple(draw(items_st)))


@st.composite
def tuples(draw, expr_st):
    items_st = internal_lists(expr_st)
    return ast.Tuple(items=tuple(draw(items_st)))


@st.composite
def calls(draw, expr_st):
    argument_st = st.tuples(names(), expr_st)
    return ast.Call(
        identifier=draw(identifiers()),
        arguments=tuple(draw(internal_lists(argument_st))),
    )


@st.composite
def unary_ops(draw, expr_st, safe):
    return ast.UnaryOp(
        operator=draw(unary_operators(safe=safe)),
        operand=draw(expr_st),
    )


@st.composite
def binary_ops(draw, expr_st, for_eval, safe):
    ok = False
    while not ok:
        ok = True
        op = ast.BinaryOp(
            left=draw(expr_st),
            operator=draw(binary_operators(safe=safe)),
            right=draw(expr_st),
        )
        if for_eval:
            # Avoid comparison chains - we don't support them yet.
            if op.operator in ast.comparison_operators:
                for operand in (op.left, op.right):
                    if (
                        type(operand) is ast.BinaryOp
                        and operand.operator in ast.comparison_operators
                    ):
                        ok = False
            # Make the lazy logical operators strict.
            if op.operator == "land":
                op = op._replace(left=True)
            if op.operator == "lor":
                op = op._replace(left=False)
    return op


def expr_extend(expr_st, for_eval, safe):
    extends = [
        functools.partial(unary_ops, safe=safe),
        functools.partial(binary_ops, for_eval=for_eval, safe=safe),
    ]
    if not for_eval:
        extends += [tuples, lists, calls, dicts]
    return st.one_of(*(extend(expr_st) for extend in extends))


def exprs(for_eval=False, safe=False):
    return st.recursive(
        expr_base(for_eval=for_eval),
        functools.partial(expr_extend, for_eval=for_eval, safe=safe),
    )


@st.composite
def imports(draw):
    return ast.Import(namespace=draw(namespaces(min_size=1, max_size=global_max_size)))


@st.composite
def includes(draw):
    return ast.Include(path=draw(strings()))


@st.composite
def bindings(draw, safe, flat=False):
    return ast.Binding(
        identifier=draw(identifiers(with_module=(not flat), flat=flat)),
        expr=draw(exprs(for_eval=safe, safe=safe)),
    )


def prelude_statements(with_imports, with_includes):
    statement_sts = []
    if with_imports:
        statement_sts.append(imports())
    if with_includes:
        statement_sts.append(includes())
    return st.one_of(*statement_sts)


def config_statement_extend(statement_st):
    return with_extend(statement_st)


def config_statements(leaf_sts, flat):
    leaf_st = st.one_of(*leaf_sts)
    if flat:
        return leaf_st
    else:
        return st.recursive(leaf_st, config_statement_extend, max_leaves=2)


@st.composite
def configs(draw, with_imports=True, with_includes=True, safe=False, flat=False):
    if with_imports or with_includes:
        prelude = draw(internal_lists(prelude_statements(with_imports, with_includes)))
    else:
        prelude = ()

    leaf_sts = [bindings(safe=safe, flat=flat)]
    statements = draw(internal_lists(config_statements(leaf_sts, flat=flat)))
    return ast.Config(statements=(tuple(prelude) + tuple(statements)))


@st.composite
def alls(draw):
    return ast.All(
        identifier=draw(identifiers(with_module=True)),
        exprs=tuple(draw(internal_lists(exprs(), allow_empty=False))),
    )


@st.composite
def rows(draw, size=None, exclude_size=None):
    if size is not None:
        expr_seq_st = st.tuples(*[exprs()] * size)
    else:
        expr_seq_st = internal_lists(exprs())
    if exclude_size is not None:
        expr_seq_st = expr_seq_st.filter(lambda l: len(l) != exclude_size)
    return ast.Row(exprs=tuple(draw(expr_seq_st)))


@st.composite
def tables(draw, correct=True):
    identifier_list = draw(internal_lists(identifiers(), min_size=1))

    n_columns = len(identifier_list)
    if correct:
        row_kwargs = {"size": n_columns}
    else:
        row_kwargs = {}

    table = ast.Table(
        header=ast.Header(identifiers=tuple(identifier_list)),
        rows=tuple(draw(internal_lists(rows(**row_kwargs), min_size=1))),
    )
    if not correct:
        row_index = draw(st.integers(min_value=0, max_value=(len(table.rows) - 1)))
        row = draw(rows(exclude_size=n_columns))
        table = table._replace(
            rows=(table.rows[:row_index] + (row,) + table.rows[(row_index + 1) :])
        )
    return table


def make_block_extend(block_type):
    @st.composite
    def blocks(draw, statement_st):
        statements = draw(internal_lists(statement_st, min_size=1))
        return block_type(statements=tuple(statements))

    return blocks


@st.composite
def with_extend(draw, statement_st):
    namespace = draw(namespaces(min_size=1, max_size=global_max_size))
    statements = draw(internal_lists(statement_st, min_size=1))
    return ast.With(namespace=namespace, statements=tuple(statements))


def sweep_statement_extend(statement_st, with_withs):
    extends = [
        make_block_extend(ast.Product),
        make_block_extend(ast.Union),
    ]
    if with_withs:
        extends.append(with_extend)
    return st.one_of(*(extend(statement_st) for extend in extends))


def sweep_statements(leaf_sts, with_withs):
    return st.recursive(
        st.one_of(*leaf_sts),
        functools.partial(sweep_statement_extend, with_withs=with_withs),
        max_leaves=2,
    )


@st.composite
def sweeps(
    draw,
    with_imports=True,
    with_includes=True,
    with_withs=True,
    force_block=False,
    leaf_sts=None,
    allow_empty=True,
):
    if with_imports or with_includes:
        prelude = draw(internal_lists(prelude_statements(with_imports, with_includes)))
    else:
        prelude = ()

    leaf_sts = leaf_sts or [bindings(safe=False), alls(), tables()]
    statements = draw(
        internal_lists(
            sweep_statements(leaf_sts, with_withs=with_withs), allow_empty=allow_empty
        )
    )
    if force_block:
        index = draw(st.integers(min_value=0, max_value=len(statements)))
        block = draw(
            sweep_statement_extend(st.one_of(*leaf_sts), with_withs=with_withs)
        )
        statements.insert(index, block)
    return ast.Sweep(statements=(tuple(prelude) + tuple(statements)))


def assert_exception_equal(actual, expected, from_gin=False):
    if from_gin:
        # Gin wraps exceptions in a way that doesn't propagate args nor the
        # exact type (???).
        assert type(actual).__name__ == type(expected).__name__
    else:
        assert type(actual) == type(expected)
        assert actual.args == expected.args


@contextlib.contextmanager
def gin_sandbox():
    # Reset all bindings, unregister all configurables etc.
    importlib.reload(gin.config)

    yield gin

    # Clean up after the test.
    importlib.reload(gin.config)


def extract_used_configurables(config):
    config = transforms.flatten_withs(config)

    configurable_to_parameters = collections.defaultdict(set)

    def render_module(path):
        if path:
            return ".".join(path)
        else:
            return None

    def identifier_module_and_name(identifier):
        return (render_module(identifier.namespace.path), identifier.name)

    def extract_from_binding_identifier(identifier):
        path = identifier.namespace.path
        if path:
            # Regular binding.
            module_and_name = (render_module(path[:-1]), path[-1])
            configurable_to_parameters[module_and_name].add(identifier.name)
        # Otherwise, it's a macro assignment - no action required.

    def extract_from_node(node):
        if type(node) in (ast.Binding, ast.All):
            extract_from_binding_identifier(node.identifier)

        if type(node) is ast.Reference:
            module_and_name = identifier_module_and_name(node.identifier)
            # Just add it to the dict.
            configurable_to_parameters[module_and_name]

        if type(node) is ast.Call:
            module_and_name = identifier_module_and_name(node.identifier)
            configurable_to_parameters[module_and_name] |= set(
                name for (name, _) in node.arguments
            )

        if type(node) is ast.Header:
            for identifier in node.identifiers:
                extract_from_binding_identifier(identifier)

        return node

    transforms.fold(extract_from_node, config)
    return configurable_to_parameters


def save_used_configurables_as_module(config, path):
    configurable_to_parameters = dict(extract_used_configurables(config))

    with open(path, "w") as f:
        f.write("import gin\n")
        for ((module, name), parameters) in configurable_to_parameters.items():
            if module == "_h" and name in ("u", "b"):
                continue

            args = ", ".join(parameters)
            f.write(f"def {name}({args}):\n")
            f.write("    return {\n")
            for param in parameters:
                f.write(f"        '{param}': {param},\n")
            f.write("    }\n")
            f.write(f"{name} = gin.external_configurable({name}")
            if module is not None:
                f.write(f', module="{module}"')
            f.write(")\n")

    with open(path, "r") as f:
        hypothesis.note("Module with configurables: " + path + "\n" + f.read())


def register_used_configurables(config):
    path = tempfile.NamedTemporaryFile(suffix=".py").name

    save_used_configurables_as_module(config, path)
    with open(path, "r") as f:
        locals = {}
        exec(f.read(), {}, locals)
        return locals


@contextlib.contextmanager
def try_in_gin_sandbox(config=None):
    with gin_sandbox() as gin:
        if config is not None:
            register_used_configurables(config)

        try:
            yield gin
        except TypeError as e:
            # The only exception we allow here, for cases like {[]: ...}.
            if "unhashable type" not in str(e):
                raise


def try_to_parse_config_using_gin(config):
    rendered_config = rendering.render(config)
    hypothesis.note(f"Rendered config: {rendered_config}")

    with try_in_gin_sandbox(config) as gin:
        gin.parse_config(rendered_config)


allowed_eval_exceptions = {OverflowError, TypeError, ValueError, ZeroDivisionError}


@contextlib.contextmanager
def try_with_eval():
    try:
        yield
    except Exception as e:
        hypothesis.assume(type(e) not in allowed_eval_exceptions)
        raise


def constants_to_macros(config):
    macro_bindings = []

    def memorize_value(x):
        if type(x) in (bool, int, float, complex):
            name = f"m{len(macro_bindings)}"
            identifier = transforms.make_identifier(namespace_path=(), name=name)
            macro_bindings.append(ast.Binding(identifier=identifier, expr=x))
            return ast.Macro(name=name)

        return x

    config = transforms.fold(memorize_value, config)
    return config._replace(statements=(config.statements + tuple(macro_bindings)))
