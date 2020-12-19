import operator as operator_lib

from hyperion import ast


def fold(f, tree):
    def fold_tuple(t):
        return tuple(fold(f, value) for value in t)

    if type(tree) is tuple:
        tree = fold_tuple(tree)
    elif type(tree) in (ast.Tuple, ast.List):
        tree = type(tree)(items=fold_tuple(tree.items))
    elif type(tree) is ast.Dict:
        tree = ast.Dict(
            items=tuple((fold(f, key), fold(f, value)) for (key, value) in tree.items)
        )
    elif isinstance(tree, tuple) and "hyperion.ast" in str(type(tree)):
        # Namedtuple.
        tree = type(tree)(*fold_tuple(tree))

    return f(tree)


def eval_unary_op(operator, operand):
    return getattr(operator_lib, operator)(operand)


def eval_binary_op(left, operator, right):
    if operator == "land":
        return left and right
    if operator == "lor":
        return left or right
    if operator == "in_":
        return left in right
    if operator == "not_in":
        return left not in right
    return getattr(operator_lib, operator)(left, right)


def partial_eval_tree(tree):
    def is_static(value):
        # For now we only support partial evaluation of numerical and logical
        # expressions.
        return type(value) in (int, float, bool)

    def eval_node(node):
        if type(node) is ast.UnaryOp and is_static(node.operand):
            return eval_unary_op(*node)

        if (
            type(node) is ast.BinaryOp
            and is_static(node.left)
            and is_static(node.right)
        ):
            return eval_binary_op(*node)

        return node

    return fold(eval_node, tree)


def partial_eval(statements):
    return list(map(partial_eval_tree, statements))


def make_identifier(namespace_path, name):
    return ast.Identifier(
        scope=ast.Scope(path=()),
        namespace=ast.Namespace(path=namespace_path),
        name=name,
    )


def expressions_to_calls(statements):
    def convert_node(node):
        if type(node) is ast.UnaryOp:
            return ast.Call(
                identifier=make_identifier(("_h",), "u"),
                arguments=(
                    ("o", ast.String(node.operator)),
                    ("v", node.operand),
                ),
            )

        if type(node) is ast.BinaryOp:
            return ast.Call(
                identifier=make_identifier(("_h",), "b"),
                arguments=(
                    ("l", node.left),
                    ("o", ast.String(node.operator)),
                    ("r", node.right),
                ),
            )

        return node

    return tuple(fold(convert_node, statement) for statement in statements)


def append_scope(scope, identifier):
    return identifier._replace(scope=ast.Scope(path=(identifier.scope.path + (scope,))))


def append_name(name, identifier):
    return identifier._replace(
        namespace=ast.Namespace(path=(identifier.namespace.path + (identifier.name,))),
        name=name,
    )


def calls_to_evaluated_references(statements):
    call_index = 0
    calls_with_args = []

    def convert_node(node):
        if type(node) is ast.Call and node.arguments:
            nonlocal call_index
            scope = f"_{call_index}"
            call_index += 1
            new_identifier = append_scope(scope, node.identifier)
            call_with_args = node._replace(identifier=new_identifier)
            calls_with_args.append(call_with_args)
            return call_with_args._replace(arguments=())

        return node

    statements = tuple(fold(convert_node, statement) for statement in statements)
    statements += tuple(
        ast.Binding(append_name(name, identifier), value)
        for (identifier, arguments) in calls_with_args
        for (name, value) in arguments
    )
    return statements


def preprocess_config(statements, with_partial_eval=True):
    if with_partial_eval:
        statements = partial_eval(statements)
    statements = expressions_to_calls(statements)
    return calls_to_evaluated_references(statements)
