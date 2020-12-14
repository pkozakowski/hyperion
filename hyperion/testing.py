import hypothesis
from hypothesis import strategies as st
from hypothesis.extra import lark as lark_st

from hyperion import ast
from hyperion import parser


unary_operators = lambda: st.one_of(*map(st.just, ast.unary_operators))
binary_operators = lambda: st.one_of(*map(st.just, ast.binary_operators))


@st.composite
def strings(draw):
    string_st = lark_st.from_lark(parser.grammar, start='STRING')
    return ast.String.from_quoted(draw(string_st))


names = lambda: lark_st.from_lark(parser.grammar, start='NAME')


@st.composite
def macros(draw):
    return ast.Macro(name=draw(names()))


@st.composite
def scopes(draw):
    return ast.Scope(path=tuple(draw(st.lists(names()))))


@st.composite
def namespaces(draw, allow_empty):
    if allow_empty:
        min_size = 0
    else:
        min_size = 1

    path_st = st.lists(names(), min_size=min_size)
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


expr_base = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(),
    strings(),
    macros(),
    references(),
)


@st.composite
def dicts(draw, expr_st):
    items_st = st.lists(st.tuples(expr_st, expr_st))
    return ast.Dict(items=tuple(draw(items_st)))


@st.composite
def lists(draw, expr_st):
    items_st = st.lists(expr_st)
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
def binary_ops(draw, expr_st):
    return ast.BinaryOp(
        left=draw(expr_st),
        operator=draw(binary_operators()),
        right=draw(expr_st),
    )


expr_extend = lambda expr_st: st.one_of(
    unary_ops(expr_st),
    binary_ops(expr_st),
    tuples(expr_st),
    lists(expr_st),
    calls(expr_st),
    dicts(expr_st),
)


exprs = lambda: st.recursive(expr_base, expr_extend)


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
    return tuple(draw(st.lists(statements())))
