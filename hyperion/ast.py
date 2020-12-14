import ast as python_ast
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
Dict = collections.namedtuple('Dict', ['items'])
List = collections.namedtuple('List', ['items'])
Tuple = collections.namedtuple('Tuple', ['items'])


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
    def from_quoted(cls, text):
        # Strip the quotes and unescape.
        return cls(python_ast.literal_eval(text))

    @classmethod
    def from_tokens(cls, tokens):
        (text,) = tokens
        return cls.from_quoted(text)


operator_chars = {
    'pow': '**',
    'pos': '+',
    'neg': '-',
    'inv': '~',
    'mul': '*',
    'truediv': '/',
    'floordiv': '//',
    'mod': '%',
    'add': '+',
    'sub': '-',
    'lshift': '<<',
    'rshift': '>>',
    'and_': '&',
    'xor': '^',
    'or_': '|',
    'eq': '==',
    'ne': '!=',
    'lt': '<',
    'gt': '>',
    'le': '<=',
    'ge': '>=',
    'is_': 'is',
    'is_not': 'is not',
    'in_': 'in',
    'not_in': 'not in',
    'not_': 'not',
    'land': 'and',
    'lor': 'or',
}
unary_operators = {'pos', 'neg', 'inv', 'not_'}
binary_operators = set(operator_chars.keys()) - unary_operators
