import functools

import hypothesis
from hypothesis import strategies as st
from hypothesis.extra import lark as lark_st

from hyperion import ast
from hyperion import parsing


max_size = 4


unary_operators = lambda: st.one_of(*map(st.just, ast.unary_operators))
binary_operators = lambda: st.one_of(*map(st.just, ast.binary_operators))


@st.composite
def strings(draw):
    string_st = st.text(
        alphabet=st.characters(blacklist_categories=("C", "Zl", "Zp")),
        max_size=max_size,
    )
    return ast.String(draw(string_st))


def names():
    name_st = lark_st.from_lark(parsing.grammar, start="NAME")
    return name_st.filter(lambda x: len(x) <= max_size)


@st.composite
def macros(draw):
    return ast.Macro(name=draw(names()))


def internal_lists(item_st, **kwargs):
    return st.lists(item_st, max_size=max_size, **kwargs)


@st.composite
def scopes(draw):
    return ast.Scope(path=tuple(draw(internal_lists(names()))))


@st.composite
def namespaces(draw, allow_empty):
    if allow_empty:
        min_size = 0
    else:
        min_size = 1

    path_st = internal_lists(names(), min_size=min_size)
    return ast.Namespace(path=tuple(draw(path_st)))


@st.composite
def identifiers(draw):
    return ast.Identifier(
        scope=draw(scopes()),
        namespace=draw(namespaces(allow_empty=True)),
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
    items_st = st.lists(expr_st)
    return ast.Tuple(items=tuple(draw(items_st)))


@st.composite
def calls(draw, expr_st):
    argument_st = st.tuples(names(), expr_st)
    return ast.Call(
        identifier=draw(identifiers()),
        arguments=tuple(draw(st.lists(argument_st))),
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


statements = lambda: st.one_of(imports(), bindings())


@st.composite
def configs(draw):
    return tuple(draw(internal_lists(statements())))


def assert_exception_equal(actual, expected):
    assert type(actual) == type(expected)
    assert actual.args == expected.args
