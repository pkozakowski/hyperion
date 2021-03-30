import ast as python_ast
import collections


# Configs:

Config = collections.namedtuple("Config", ["statements"])
Import = collections.namedtuple("Import", ["namespace"])
Include = collections.namedtuple("Include", ["path"])
Namespace = collections.namedtuple("Namespace", ["path"])
Binding = collections.namedtuple("Binding", ["identifier", "expr"])
Identifier = collections.namedtuple("Identifier", ["scope", "namespace", "name"])
Scope = collections.namedtuple("Scope", ["path"])
Macro = collections.namedtuple("Macro", ["name"])
Reference = collections.namedtuple("Reference", ["identifier"])
UnaryOp = collections.namedtuple("UnaryOp", ["operator", "operand"])
BinaryOp = collections.namedtuple("BinaryOp", ["left", "operator", "right"])
Parenthesis = collections.namedtuple("Parenthesis", ["expr"])
Dict = collections.namedtuple("Dict", ["items"])
List = collections.namedtuple("List", ["items"])
Tuple = collections.namedtuple("Tuple", ["items"])


class Call(collections.namedtuple("Call", ["identifier", "arguments"])):
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


operator_to_chars_and_precedence = {
    # Exponentiation:
    "pow": ("**", 2),
    # Unary arithmetic and bitwise operators:
    "pos": ("+", 3),
    "neg": ("-", 3),
    "inv": ("~", 3),
    # Arithmetics:
    "mul": ("*", 4),
    "truediv": ("/", 4),
    "floordiv": ("//", 4),
    "mod": ("%", 4),
    "add": ("+", 5),
    "sub": ("-", 5),
    # Bitwise operators:
    "lshift": ("<<", 6),
    "rshift": (">>", 6),
    "and_": ("&", 7),
    "xor": ("^", 8),
    "or_": ("|", 9),
    # Comparison and membership:
    "eq": ("==", 10),
    "ne": ("!=", 10),
    "lt": ("<", 10),
    "gt": (">", 10),
    "le": ("<=", 10),
    "ge": (">=", 10),
    "in_": ("in", 10),
    "not_in": ("not in", 10),
    # Logic:
    "not_": ("not ", 11),
    "land": ("and", 12),
    "lor": ("or", 13),
}
all_operators = set(operator_to_chars_and_precedence)
unary_operators = {"pos", "neg", "inv", "not_"}
binary_operators = all_operators - unary_operators
comparison_operators = {
    "eq",
    "ne",
    "lt",
    "gt",
    "le",
    "ge",
    "in_",
    "not_in",
}
safe_unary_operators = {"pos", "neg"}
safe_binary_operators = {"add", "sub", "mul"}


def operator_chars(operator):
    (chars, _) = operator_to_chars_and_precedence[operator]
    return chars


def operator_precedence(operator):
    (_, precedence) = operator_to_chars_and_precedence[operator]
    return precedence


# Sweeps:

Sweep = collections.namedtuple("Sweep", ["statements"])
All = collections.namedtuple("All", ["identifier", "exprs"])
Product = collections.namedtuple("Product", ["statements"])
Union = collections.namedtuple("Union", ["statements"])
Table = collections.namedtuple("Table", ["header", "rows"])
Header = collections.namedtuple("Header", ["identifiers"])
Row = collections.namedtuple("Row", ["exprs"])
