import collections
import os

import lark


class Import(collections.namedtuple('Import', ['namespace'])):

    def __str__(self):
        return 'import ' + str(self.namespace)


class Namespace(collections.namedtuple('Namespace', ['path'])):

    def __str__(self):
        return '.'.join(self.path)


class Binding(collections.namedtuple('Binding', ['identifier', 'expr'])):

    def __str__(self):
        return str(self.identifier) + ' = ' + str(self.expr)


class Identifier(
    collections.namedtuple('Identifier', ['scope', 'namespace', 'name'])
):

    def __str__(self):
        scope = str(self.scope)
        if scope:
            scope += '/'

        namespace = str(self.namespace)
        if namespace:
            namespace += '.'

        return scope + namespace + self.name


class Scope(collections.namedtuple('Scope', ['path'])):

    def __str__(self):
        return '/'.join(self.path)


class Dict(dict):

    def __str__(self):
        return '{' + ', '.join(
            f'{k}: {v}' for (k, v) in self.items()
        ) + '}'


class List(list):

    def __str__(self):
        return '[' + ', '.join(map(str, self)) + ']'


class Tuple(tuple):

    def __str__(self):
        if len(self) == 1:
            return f'({self[0]},)'
        else:
            return '(' + ', '.join(map(str, self)) + ')'


class Macro(collections.namedtuple('Macro', ['name'])):

    def __str__(self):
        return '%' + self.name


class Reference(collections.namedtuple('Reference', ['identifier'])):

    def __str__(self):
        return '@' + str(self.identifier)


class Call(collections.namedtuple('Call', ['identifier', 'arguments'])):

    @classmethod
    def _make(cls, items):
        identifier = items[0]
        arguments = []
        if len(items) > 1:
            (arguments,) = items[1:]
        return Call(identifier, arguments)

    def __str__(self):
        args = ', '.join(
            f'{name}={value}'.format(name, value)
            for (name, value) in self.arguments
        )
        return f'@{self.identifier}({args})'


class String(str):

    def __new__(cls, items):
        (text,) = items
        # Strip the quotes.
        return super().__new__(cls, text[1:-1])

    def __str__(self):
        # Add the quotes.
        return repr(self)


class GinTransformer(lark.Transformer):

    def identifier(self, items):
        scope = Scope(path=[])
        namespace = Namespace(path=[])
        name = None
        for item in items:
            if isinstance(item, Scope):
                scope = item
            elif isinstance(item, Namespace):
                namespace = item
            else:
                name = item
        return Identifier(scope=scope, namespace=namespace, name=name)

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
    import_ = Import._make
    binding = Binding._make
    scope = Scope
    namespace = Namespace

    dict = Dict
    entry = tuple
    list = List
    tuple = Tuple
    cs_list = list

    macro = Macro._make
    reference = Reference._make
    call = Call._make
    argument = tuple
    string = String

    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False


grammar_path = os.path.join(os.path.dirname(__file__), 'grammar.lark')
with open(grammar_path, 'r') as f:
    _parser = lark.Lark(f.read(), start='start')


def parse_bindings(text):
    parse_tree = _parser.parse(text)
    statements = GinTransformer().transform(parse_tree)
    config = '\n'.join(map(str, statements))
    return config


def parse_config_file(path):
    with open(path, 'r') as f:
        return parse_bindings(f.read())
