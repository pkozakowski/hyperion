from hyperion import ast
from hyperion import transforms


def render_config_or_sweep(config_or_sweep):
    return "\n".join(config_or_sweep.statements)


def render_identifier(node):
    scope = node.scope
    if scope:
        scope += "/"

    namespace = node.namespace
    if namespace:
        namespace += "."

    return scope + namespace + node.name


def render_binding(node):
    (expr, _) = node.expr
    return f"{node.identifier} = {expr}"


# The expression rendering functions return pairs (text, precedence).


def extract_expr(item):
    (expr, _) = item
    return expr


def extract_exprs(seq):
    return tuple(map(extract_expr, seq))


def render_dict(node):
    text = (
        "{"
        + ", ".join(
            f"{extract_expr(key)}: {extract_expr(value)}" for (key, value) in node.items
        )
        + "}"
    )
    return (text, 0)


def render_list(node):
    exprs = extract_exprs(node.items)
    text = "[" + ", ".join(map(str, exprs)) + "]"
    return (text, 0)


def render_tuple(node):
    exprs = extract_exprs(node.items)
    if len(exprs) == 1:
        text = f"({exprs[0]},)"
    else:
        text = "(" + ", ".join(map(str, exprs)) + ")"
    return (text, 0)


def render_call(node):
    args = ", ".join(
        f"{name}={extract_expr(value)}" for (name, value) in node.arguments
    )
    return (f"@{node.identifier}({args})", 1)


def render_unary_op(node):
    operator_chars = ast.operator_chars(node.operator)
    (operand_text, operand_precedence) = node.operand
    precedence = ast.operator_precedence(node.operator)
    if operand_precedence > precedence:
        operand_text = f"({operand_text})"
    text = f"{operator_chars}{operand_text}"
    return (text, precedence)


def render_binary_op(node):
    (left_text, left_precedence) = node.left
    operator_chars = ast.operator_chars(node.operator)
    (right_text, right_precedence) = node.right
    precedence = ast.operator_precedence(node.operator)
    if left_precedence > precedence:
        left_text = f"({left_text})"
    # >= because of left-to-right chaining.
    if right_precedence >= precedence:
        right_text = f"({right_text})"
    text = f"{left_text} {operator_chars} {right_text}"
    return (text, precedence)


def render_all(node):
    exprs = extract_exprs(node.exprs)
    return f"{node.identifier}: [" + ", ".join(map(str, exprs)) + "]"


def add_indent(text):
    indent = "    "
    return indent + text.replace("\n", "\n" + indent)


def render_block(node):
    name = {ast.Product: "product", ast.Union: "union"}[type(node)]
    return f"{name}:\n" + "\n".join(map(add_indent, node.statements))


def render_table(node):
    return f"table {node.header}:\n" + "\n".join(map(add_indent, node.rows))


def render_row(node):
    exprs = extract_exprs(node.exprs)
    return ", ".join(map(str, exprs))


def render_node(node):
    render_map = {
        # Configs:
        ast.Config: render_config_or_sweep,
        ast.Import: lambda node: f"import {node.namespace}",
        ast.Namespace: lambda node: ".".join(node.path),
        ast.Binding: render_binding,
        ast.Identifier: render_identifier,
        ast.Scope: lambda node: "/".join(node.path),
        ast.UnaryOp: render_unary_op,
        ast.BinaryOp: render_binary_op,
        ast.Dict: render_dict,
        ast.List: render_list,
        ast.Tuple: render_tuple,
        ast.Macro: lambda node: (f"%{node.name}", 0),
        ast.Reference: lambda node: (f"@{node.identifier}", 0),
        ast.Call: render_call,
        ast.String: lambda node: (
            repr(node),  # Add quotes.
            0,
        ),
        str: lambda node: node,  # Name.
        tuple: lambda node: node,  # Internal sequence, e.g. namespace path.
        # Sweeps:
        ast.Sweep: render_config_or_sweep,
        ast.All: render_all,
        ast.Product: render_block,
        ast.Union: render_block,
        ast.Table: render_table,
        ast.Header: lambda node: ", ".join(node.identifiers),
        ast.Row: render_row,
    }

    if type(node) in render_map:
        return render_map[type(node)](node)
    else:
        # Primitive literals - expressions with precedence 0.
        return (str(node), 0)


def render(tree):
    return transforms.fold(render_node, tree)
