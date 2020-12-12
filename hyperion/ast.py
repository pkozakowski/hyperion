import collections


Import = collections.namedtuple('Import', ['namespace'])
Namespace = collections.namedtuple('Namespace', ['path'])
Binding = collections.namedtuple('Binding', ['identifier', 'expr'])
Identifier = collections.namedtuple(
    'Identifier', ['scope', 'namespace', 'name']
)
Scope = collections.namedtuple('Scope', ['path'])
Macro = collections.namedtuple('Macro', ['name'])
Reference = collections.namedtuple('Reference', ['identifier'])
UnaryOp = collections.namedtuple('UnaryOp', ['operator', 'operand'])
BinaryOp = collections.namedtuple('BinaryOp', ['left', 'operator', 'right'])


class Dict(dict): pass
class List(list): pass
class Tuple(tuple): pass


class Call(collections.namedtuple('Call', ['identifier', 'arguments'])):

    @classmethod
    def _make(cls, items):
        items = list(items)
        identifier = items[0]
        arguments = []
        if len(items) > 1:
            (arguments,) = items[1:]
        return Call(identifier, arguments)


class String(str):

    @classmethod
    def from_tokens(cls, tokens):
        (text,) = tokens
        # Strip the quotes.
        return cls(text[1:-1])
