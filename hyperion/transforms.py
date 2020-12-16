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


def make_identifier(namespace_path, name):
    return ast.Identifier(
        scope=ast.Scope(path=[]),
        namespace=ast.Namespace(path=namespace_path),
        name=name,
    )


def expressions_to_calls(statements):
    def convert_node(node):
        if type(node) is ast.UnaryOp:
            return ast.Call(
                identifier=make_identifier(["hyperion", "gin"], "_eval_unary"),
                arguments=[
                    ("op", ast.String(node.operator)),
                    ("v", node.operand),
                ],
            )

        if type(node) is ast.BinaryOp:
            return ast.Call(
                identifier=make_identifier(["hyperion", "gin"], "_eval_binary"),
                arguments=[
                    ("l", node.left),
                    ("op", ast.String(node.operator)),
                    ("r", node.right),
                ],
            )

        return node

    return [fold(convert_node, statement) for statement in statements]


def append_scope(scope, identifier):
    return identifier._replace(scope=ast.Scope(path=(identifier.scope.path + [scope])))


def append_name(name, identifier):
    return identifier._replace(
        namespace=ast.Namespace(path=(identifier.namespace.path + [identifier.name])),
        name=name,
    )


def calls_to_evaluated_references(statements):
    call_index = 1
    calls_with_args = []

    def convert_node(node):
        if type(node) is ast.Call and node.arguments:
            nonlocal call_index
            scope = f"_call_{call_index}"
            call_index += 1
            new_identifier = append_scope(scope, node.identifier)
            call_with_args = node._replace(identifier=new_identifier)
            calls_with_args.append(call_with_args)
            return call_with_args._replace(arguments=[])

        return node

    statements = [fold(convert_node, statement) for statement in statements]
    statements += [
        ast.Binding(append_name(name, identifier), value)
        for (identifier, arguments) in calls_with_args
        for (name, value) in arguments
    ]
    return statements


def preprocess_config(statements):
    statements = expressions_to_calls(statements)
    return calls_to_evaluated_references(statements)
