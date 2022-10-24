import ast as python_ast
import collections


# Modification of namedtuple that takes the type name into account when hashing.
def hashable_namedtuple(name, fields):
    namedtuple_class = collections.namedtuple(name, fields)

    def hash_with_name(self):
        return hash((namedtuple_class.__name__, tuple(self)))

    namedtuple_class.__hash__ = hash_with_name
    return namedtuple_class


# Configs:

Config = hashable_namedtuple("Config", ["statements"])
Import = hashable_namedtuple("Import", ["namespace"])
Include = hashable_namedtuple("Include", ["path"])
Namespace = hashable_namedtuple("Namespace", ["path"])
Binding = hashable_namedtuple("Binding", ["identifier", "expr"])
Identifier = hashable_namedtuple("Identifier", ["scope", "namespace", "name"])
Scope = hashable_namedtuple("Scope", ["path"])
With = hashable_namedtuple("With", ["namespace", "statements"])
Macro = hashable_namedtuple("Macro", ["name"])
Reference = hashable_namedtuple("Reference", ["identifier"])
UnaryOp = hashable_namedtuple("UnaryOp", ["operator", "operand"])
BinaryOp = hashable_namedtuple("BinaryOp", ["left", "operator", "right"])
Parenthesis = hashable_namedtuple("Parenthesis", ["expr"])
Dict = hashable_namedtuple("Dict", ["items"])
List = hashable_namedtuple("List", ["items"])
Tuple = hashable_namedtuple("Tuple", ["items"])


class Call(hashable_namedtuple("Call", ["identifier", "arguments"])):
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

Sweep = hashable_namedtuple("Sweep", ["statements"])
All = hashable_namedtuple("All", ["identifier", "exprs"])
Product = hashable_namedtuple("Product", ["statements"])
Union = hashable_namedtuple("Union", ["statements"])
Table = hashable_namedtuple("Table", ["header", "rows"])
Header = hashable_namedtuple("Header", ["identifiers"])
Row = hashable_namedtuple("Row", ["exprs"])
