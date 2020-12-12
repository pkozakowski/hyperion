import collections


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
        items = list(items)
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
