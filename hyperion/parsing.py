import os

import lark
from lark import indenter

from hyperion import ast
from hyperion import transforms


class ConfigTransformer(lark.Transformer):
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

    config = lambda self, statements: ast.Config(tuple(statements))
    import_ = ast.Import._make
    include = lambda self, tokens: ast.Include(path=ast.String.from_tokens(tokens))
    binding = ast.Binding._make
    scope = lambda self, path: ast.Scope(tuple(path))
    namespace = lambda self, path: ast.Namespace(tuple(path))
    entry = tuple
    argument = tuple
    cs_list = tuple
    _cs_list = tuple
    parenthesis = ast.Parenthesis._make

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
        # Choose the option where an operation of the same precedence as the root
        # is on the left-hand side, and the one on the right-hand side, if any,
        # has different precedence. If it's exponentiation, do the reverse.
        for root in options:
            if root.operator == "pow":
                chained = root.right
                other = root.left
            else:
                chained = root.left
                other = root.right

            if type(chained) is not ast.BinaryOp:
                continue

            if type(other) is ast.BinaryOp:
                other_precedence = ast.operator_precedence(other.operator)
            else:
                # Parentheses also fall here.
                other_precedence = 0

            root_precedence = ast.operator_precedence(root.operator)
            chained_precedence = ast.operator_precedence(chained.operator)
            if root_precedence == chained_precedence != other_precedence:
                return root


def unary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, operand):
        return ast.UnaryOp(operator, operand)

    return transform


for op in ast.unary_operators:
    setattr(ConfigTransformer, op, unary_op(op))


def binary_op(operator):
    @lark.v_args(inline=True)
    def transform(self, left, right):
        return ast.BinaryOp(left, operator, right)

    return transform


for op in ast.binary_operators:
    setattr(ConfigTransformer, op, binary_op(op))


class BlockIndenter(indenter.Indenter):
    NL_type = "_NL"
    OPEN_PAREN_types = ["_LPAREN", "_LBRACKET", "_LBRACE"]
    CLOSE_PAREN_types = ["_RPAREN", "_RBRACKET", "_RBRACE"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


def open_grammar(name, start):
    grammar_path = os.path.dirname(__file__)
    return lark.Lark.open(
        os.path.join(grammar_path, name),
        import_paths=[grammar_path],
        start=start,
        parser="earley",
        lexer="standard",
        ambiguity="explicit",
        postlex=BlockIndenter(),
    )


config_grammar = open_grammar("config.lark", "config")
expr_grammar = open_grammar("config.lark", "expr")


def remove_parentheses(tree):
    def remove_parenthesis(node):
        if type(node) is ast.Parenthesis:
            return node.expr
        return node

    return transforms.fold(remove_parenthesis, tree)


def parse_config(text):
    parse_tree = config_grammar.parse(text)
    tree = ConfigTransformer().transform(parse_tree)
    # We only need parentheses for resolving ambiguities, so we remove them
    # right after parsing.
    return remove_parentheses(tree)


def parse_expr(text):
    parse_tree = expr_grammar.parse(text)
    tree = ConfigTransformer().transform(parse_tree)
    return remove_parentheses(tree)


class SweepTransformer(lark.Transformer):

    sweep = lambda self, statements: ast.Sweep(tuple(statements))
    all = ast.All._make
    product = lambda self, statements: ast.Product(tuple(statements))
    union = lambda self, statements: ast.Union(tuple(statements))
    table = lambda self, items: ast.Table(header=items[0], rows=tuple(items[1:]))
    table_header = lambda self, identifiers: ast.Header(tuple(identifiers))
    table_row = lambda self, exprs: ast.Row(tuple(exprs))


# Copy the ConfigTransformer visitors into SweepTransformer with the config__ prefix.
# The prefix is added when importing config.lark from sweep.lark.
for unprefixed_name in set(dir(ConfigTransformer)) - set(dir(lark.Transformer)):
    for name in (unprefixed_name, "config__" + unprefixed_name):
        setattr(SweepTransformer, name, getattr(ConfigTransformer, unprefixed_name))


sweep_grammar = open_grammar("sweep.lark", "sweep")


def parse_sweep(text):
    text += "\n"
    parse_tree = sweep_grammar.parse(text)
    tree = SweepTransformer().transform(parse_tree)
    return remove_parentheses(tree)
