import collections
import contextlib
import functools
import importlib
import string

import gin
import hypothesis
from hypothesis import strategies as st

from hyperion import ast
from hyperion import parsing
from hyperion import rendering
from hyperion import transforms


max_size = 2


unary_operators = lambda: st.one_of(*map(st.just, ast.unary_operators))
binary_operators = lambda: st.one_of(*map(st.just, ast.binary_operators))


@st.composite
def strings(draw):
    string_st = st.text(
        alphabet=st.characters(blacklist_categories=("C", "Zl", "Zp")),
        max_size=max_size,
    )
    return ast.String(draw(string_st))


@st.composite
def names(draw):
    keywords = {"import", "in", "not", "and", "or", "product", "union", "table"}

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
                max_size=(max_size - 1),
            )
        )
        name = first + rest

    return name


@st.composite
def macros(draw):
    return ast.Macro(name=draw(names()))


def internal_lists(item_st, allow_empty=True, **kwargs):
    if not allow_empty:
        kwargs["min_size"] = 1
    return st.lists(item_st, max_size=max_size, **kwargs)


@st.composite
def scopes(draw):
    return ast.Scope(path=tuple(draw(internal_lists(names()))))


@st.composite
def namespaces(draw, allow_empty):
    path_st = internal_lists(names(), allow_empty=allow_empty)
    return ast.Namespace(path=tuple(draw(path_st)))


@st.composite
def identifiers(draw):
    return ast.Identifier(
        scope=draw(scopes()),
        namespace=draw(namespaces(allow_empty=False)),
        name=draw(names()),
    )


@st.composite
def references(draw):
    return ast.Reference(identifier=draw(identifiers()))


def expr_base(for_eval):
    base_sts = [
        st.booleans(),
        st.integers(min_value=0),
        st.floats(min_value=0.0, allow_infinity=False, allow_nan=False),
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
def unary_ops(draw, expr_st):
    return ast.UnaryOp(
        operator=draw(unary_operators()),
        operand=draw(expr_st),
    )


@st.composite
def binary_ops(draw, expr_st, for_eval):
    ok = False
    while not ok:
        ok = True
        op = ast.BinaryOp(
            left=draw(expr_st),
            operator=draw(binary_operators()),
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


def expr_extend(expr_st, for_eval):
    extends = [unary_ops, functools.partial(binary_ops, for_eval=for_eval)]
    if not for_eval:
        extends += [tuples, lists, calls, dicts]
    return st.one_of(*(extend(expr_st) for extend in extends))


def exprs(for_eval=False):
    return st.recursive(
        expr_base(for_eval=for_eval),
        functools.partial(expr_extend, for_eval=for_eval),
    )


@st.composite
def imports(draw):
    return ast.Import(namespace=draw(namespaces(allow_empty=False)))


@st.composite
def bindings(draw):
    return ast.Binding(
        identifier=draw(identifiers()),
        expr=draw(exprs()),
    )


def config_statements(with_imports):
    statement_sts = []
    if with_imports:
        statement_sts.append(imports())
    statement_sts.append(bindings())
    return st.one_of(*statement_sts)


@st.composite
def configs(draw, with_imports=True, allow_empty=True):
    statements = draw(internal_lists(config_statements(with_imports=with_imports)))
    return ast.Config(statements=tuple(statements))


@st.composite
def alls(draw):
    return ast.All(
        identifier=draw(identifiers()),
        exprs=tuple(draw(internal_lists(exprs(), allow_empty=False))),
    )


@st.composite
def rows(draw):
    return ast.Row(exprs=tuple(draw(internal_lists(exprs(), min_size=1))))


@st.composite
def tables(draw):
    identifier_list = draw(internal_lists(identifiers(), min_size=1))
    return ast.Table(
        header=ast.Header(identifiers=tuple(identifier_list)),
        rows=tuple(draw(internal_lists(rows(), min_size=1))),
    )


def make_blocks(block_type):
    @st.composite
    def blocks(draw, statement_st):
        statements = draw(internal_lists(statement_st, min_size=1))
        return block_type(statements=tuple(statements))

    return blocks


def sweep_statement_extend(statement_st):
    extends = [make_blocks(ast.Product), make_blocks(ast.Union)]
    return st.one_of(*(extend(statement_st) for extend in extends))


def sweep_statements(with_imports, leaf_sts):
    leaf_sts = leaf_sts or (
        config_statements(with_imports=False),
        alls(),
        tables(),
    )
    return st.one_of(
        imports(),
        st.recursive(
            st.one_of(*leaf_sts),
            sweep_statement_extend,
            max_leaves=3,
        ),
    )


@st.composite
def sweeps(draw, with_imports=True, leaf_sts=None, allow_empty=True):
    statements = draw(
        internal_lists(
            sweep_statements(with_imports=with_imports, leaf_sts=leaf_sts),
            allow_empty=allow_empty,
        )
    )
    return ast.Sweep(statements=tuple(statements))


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
    configurable_to_parameters = collections.defaultdict(set)

    def render_module(path):
        if path:
            return ".".join(path)
        else:
            return None

    def identifier_module_and_name(identifier):
        return (render_module(identifier.namespace.path), identifier.name)

    def extract_from_node(node):
        if type(node) is ast.Binding:
            path = node.identifier.namespace.path
            if path:
                # Regular binding.
                module_and_name = (render_module(path[:-1]), path[-1])
                configurable_to_parameters[module_and_name].add(node.identifier.name)
            # Otherwise, it's a macro assignment - no action required.

        if type(node) in (ast.Reference, ast.Call):
            module_and_name = identifier_module_and_name(node.identifier)
            # Just add it to the dict.
            configurable_to_parameters[module_and_name]

        if type(node) is ast.Macro:
            module_and_name = (None, node.name)
            # Macros are just configurables with an argument `value`.
            configurable_to_parameters[module_and_name].add("value")

        return node

    transforms.fold(extract_from_node, config)
    return configurable_to_parameters


def register_used_configurables(gin, statements):
    configurable_to_parameters = dict(extract_used_configurables(statements))
    hypothesis.note(
        f"Registering configurables with parameters: {configurable_to_parameters}"
    )

    for ((module, name), parameters) in configurable_to_parameters.items():
        args = ", ".join(parameters)
        f = eval(f"lambda {args}: None", {}, {})
        gin.external_configurable(f, module=module, name=name)


allowed_eval_exceptions = {OverflowError, TypeError, ValueError, ZeroDivisionError}
