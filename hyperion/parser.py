import os

import lark

from hyperion import ast


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

    dict = ast.Dict
    entry = tuple
    list = ast.List
    tuple = ast.Tuple
    cs_list = list

    macro = ast.Macro._make
    reference = ast.Reference._make
    call = ast.Call._make
    argument = tuple
    string = ast.String

    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False


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
