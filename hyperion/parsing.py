import os

import lark

from hyperion import ast


class GinTransformer(lark.Transformer):
    def identifier(self, items):
        scope = ast.Scope(path=())
        namespace = ast.Namespace(path=())
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

    @lark.v_args(inline=True)
    def call(self, identifier, arguments=()):
        return ast.Call(identifier, tuple(arguments))

    start = tuple
    import_ = ast.Import._make
    binding = ast.Binding._make
    scope = lambda self, path: ast.Scope(tuple(path))
    namespace = lambda self, path: ast.Namespace(tuple(path))
    entry = tuple
    argument = tuple
    cs_list = tuple
    _cs_list = tuple

    macro = ast.Macro._make
    reference = ast.Reference._make
    string = ast.String.from_tokens

    dict = lambda self, items: ast.Dict(tuple(items))
    list = lambda self, items: ast.List(tuple(items))
    tuple = lambda self, items: ast.Tuple(tuple(items))

    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False

    def _ambig(self, options):
        # Ambiguity occurs only for binary operators.
        assert all(type(option) is ast.BinaryOp for option in options)
        # Choose the option where an operation of the same precedence as the
        # root is on the left-hand side.
        for root in options:
            if type(root.left) is not ast.BinaryOp:
                continue
            root_precedence = ast.operator_precedence(root.operator)
            left_precedence = ast.operator_precedence(root.left.operator)
            if root_precedence == left_precedence:
                return root


def unary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, operand):
        return ast.UnaryOp(operator, operand)

    return transform


for op in ast.unary_operators:
    setattr(GinTransformer, op, unary_op(op))


def binary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, left, right):
        return ast.BinaryOp(left, operator, right)

    return transform


for op in ast.binary_operators:
    setattr(GinTransformer, op, binary_op(op))


grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
with open(grammar_path, "r") as f:
    grammar = lark.Lark(
        f.read(),
        parser="earley",
        ambiguity="explicit",
        start="start",
    )


def parse_config(text):
    parse_tree = grammar.parse(text)
    statements = GinTransformer().transform(parse_tree)
    return statements
