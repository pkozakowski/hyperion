from hyperion import ast


def fold(f, tree):
    def fold_seq(seq):
        return type(seq)(fold(f, value) for value in seq)

    if isinstance(tree, (ast.List, ast.Tuple)):
        tree = fold_seq(tree)
    elif isinstance(tree, ast.Dict):
        tree = ast.Dict(
            (fold(f, key), fold(f, value)) for (key, value) in tree.items()
        )
    elif isinstance(tree, tuple):
        if 'hyperion.ast' in str(type(tree)):
            # Namedtuple.
            tree = type(tree)(*[fold(f, child) for child in tree])
        else:
            # Ordinary tuple.
            tree = fold_seq(tree)

    return f(tree)


def append_scope(scope, identifier):
    return identifier._replace(
        scope=ast.Scope(path=(identifier.scope.path + [scope]))
    )


def append_name(name, identifier):
    return identifier._replace(
        namespace=ast.Namespace(
            path=(identifier.namespace.path + [identifier.name])
        ),
        name=name,
    )


def calls_to_evaluated_references(statements):
    call_index = 1
    calls_with_args = []

    def convert_node(node):
        if isinstance(node, ast.Call) and node.arguments:
            nonlocal call_index
            scope = f'_call_{call_index}'
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


def expressions_to_evaluated_references(statements):
    raise NotImplementedError
