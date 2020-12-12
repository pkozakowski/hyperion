import os

import lark

from hyperion import ast


def unary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, operand):
        return ast.UnaryOp(operator, operand)
    return transform


def binary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, left, right):
        return ast.BinaryOp(left, operator, right)
    return transform


class GinTransformer(lark.Transformer):

    def identifier(self, items):
        scope = ast.Scope(path=[])
        namespace = ast.Namespace(path=[])
        name = None
        for item in items:
            if isinstance(item, ast.Scope):
                scope = item
            elif isinstance(item, ast.Namespace):
                namespace = item
            else:
                name = item
        return ast.Identifier(scope=scope, namespace=namespace, name=name)

    @lark.v_args(inline=True)
    def name(self, token):
        return token.value
    
    @lark.v_args(inline=True)
    def number(self, token):
        text = token.value
        try:
            return int(text)
        except (TypeError, ValueError):
            return float(text)

    start = list
    import_ = ast.Import._make
    binding = ast.Binding._make
    scope = ast.Scope
    namespace = ast.Namespace
    entry = tuple
    cs_list = list

    macro = ast.Macro._make
    reference = ast.Reference._make
    call = ast.Call._make
    argument = tuple
    string = ast.String

    dict = ast.Dict
    list = ast.List
    tuple = ast.Tuple

    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False

    pow = binary_op('pow')
    pos = unary_op('pos')
    neg = unary_op('neg')
    inv = unary_op('inv')
    mul = binary_op('mul')
    truediv = binary_op('truediv')
    floordiv = binary_op('floordiv')
    mod = binary_op('mod')
    add = binary_op('add')
    sub = binary_op('sub')
    lshift = binary_op('lshift')
    rshift = binary_op('rshift')
    and_ = binary_op('and_')
    xor = binary_op('xor')
    or_ = binary_op('or_')
    eq = binary_op('eq')
    ne = binary_op('ne')
    lt = binary_op('lt')
    gt = binary_op('gt')
    le = binary_op('le')
    ge = binary_op('ge')
    is_ = binary_op('is_')
    is_not = binary_op('is_not')
    in_ = binary_op('in_')
    not_in = binary_op('not_in')
    not_ = binary_op('not_')


grammar_path = os.path.join(os.path.dirname(__file__), 'grammar.lark')
with open(grammar_path, 'r') as f:
    _parser = lark.Lark(f.read(), start='start')


def parse_bindings(text):
    parse_tree = _parser.parse(text)
    statements = GinTransformer().transform(parse_tree)
    return statements


def parse_config_file(path):
    with open(path, 'r') as f:
        return parse_bindings(f.read())
