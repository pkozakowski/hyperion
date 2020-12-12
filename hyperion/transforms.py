from hyperion import ast


def fold(f, tree):
    def fold_seq(seq):
        return type(seq)(fold(f, value) for value in seq)

    if type(tree) in (ast.List, ast.Tuple, tuple):
        tree = fold_seq(tree)
    elif type(tree) is ast.Dict:
        tree = ast.Dict(
            (fold(f, key), fold(f, value)) for (key, value) in tree.items()
        )
    elif isinstance(tree, tuple) and 'hyperion.ast' in str(type(tree)):
        # Namedtuple.
        tree = type(tree)(*[fold(f, child) for child in tree])

    return f(tree)


def render(statements):
    def render_node(node):
        def render_identifier():
            scope = node.scope
            if scope:
                scope += '/'

            namespace = node.namespace
            if namespace:
                namespace += '.'

            return scope + namespace + node.name

        def render_tuple():
            if len(node) == 1:
                return f'({node[0]},)'
            else:
                return '(' + ', '.join(map(str, node)) + ')'

        def render_call():
            args = ', '.join(
                f'{name}={value}'.format(name, value)
                for (name, value) in node.arguments
            )
            return f'@{node.identifier}({args})'

        render_table = {
            ast.Import: lambda: f'import {node.namespace}',
            ast.Namespace: lambda: '.'.join(node.path),
            ast.Binding: lambda: (
                f'{node.identifier} = {node.expr}'
            ),
            ast.Identifier: render_identifier,
            ast.Scope: lambda: '/'.join(node.path),
            ast.Dict: lambda: '{' + ', '.join(
                f'{k}: {v}' for (k, v) in node.items()
            ) + '}',
            ast.List: lambda: '[' + ', '.join(map(str, node)) + ']',
            ast.Tuple: render_tuple,
            ast.Macro: lambda: f'%{node.name}',
            ast.Reference: lambda: f'@{node.identifier}',
            ast.Call: render_call,
            ast.String: lambda: repr(node),  # Add quotes.
        }

        if type(node) in render_table:
            return render_table[type(node)]()
        else:
            return node

    return '\n'.join(fold(render_node, statement) for statement in statements)


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
        if type(node) is ast.Call and node.arguments:
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
