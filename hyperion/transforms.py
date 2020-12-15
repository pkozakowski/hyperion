from hyperion import ast


def fold(f, tree):
    def fold_tuple(t):
        return tuple(fold(f, value) for value in t)

    if type(tree) is tuple:
        tree = fold_tuple(tree)
    elif type(tree) in (ast.Tuple, ast.List):
        tree = type(tree)(items=fold_tuple(tree.items))
    elif type(tree) is ast.Dict:
        tree = ast.Dict(items=tuple(
            (fold(f, key), fold(f, value)) for (key, value) in tree.items
        ))
    elif isinstance(tree, tuple) and 'hyperion.ast' in str(type(tree)):
        # Namedtuple.
        tree = type(tree)(*fold_tuple(tree))

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

        def render_binding():
            (expr, _) = node.expr
            return f'{node.identifier} = {expr}'

        # The expression rendering functions return pairs (text, precedence).

        def extract_expr(item):
            (expr, _) = item
            return expr

        def extract_exprs(seq):
            return tuple(map(extract_expr, seq))

        def render_dict():
            text = '{' + ', '.join(
                f'{extract_expr(key)}: {extract_expr(value)}'
                for (key, value) in node.items
            ) + '}'
            return (text, 0)

        def render_list():
            exprs = extract_exprs(node.items)
            text = '[' + ', '.join(map(str, exprs)) + ']'
            return (text, 0)

        def render_tuple():
            exprs = extract_exprs(node.items)
            if len(exprs) == 1:
                text = f'({exprs[0]},)'
            else:
                text = '(' + ', '.join(map(str, exprs)) + ')'
            return (text, 0)

        def render_call():
            args = ', '.join(
                f'{name}={extract_expr(value)}'
                for (name, value) in node.arguments
            )
            return (f'@{node.identifier}({args})', 1)

        def render_unary_op():
            operator_chars = ast.operator_chars(node.operator)
            (operand_text, operand_precedence) = node.operand
            precedence = ast.operator_precedence(node.operator)
            if operand_precedence > precedence:
                operand_text = f'({operand_text})'
            text = f'{operator_chars}{operand_text}'
            return (text, precedence)

        def render_binary_op():
            (left_text, left_precedence) = node.left
            operator_chars = ast.operator_chars(node.operator)
            (right_text, right_precedence) = node.right
            precedence = ast.operator_precedence(node.operator)
            if left_precedence > precedence:
                left_text = f'({left_text})'
            # >= because of left-to-right chaining.
            if right_precedence >= precedence:
                right_text = f'({right_text})'
            text = f'{left_text} {operator_chars} {right_text}'
            return (text, precedence)

        render_table = {
            ast.Import: lambda: f'import {node.namespace}',
            ast.Namespace: lambda: '.'.join(node.path),
            ast.Binding: render_binding,
            ast.Identifier: render_identifier,
            ast.Scope: lambda: '/'.join(node.path),
            ast.UnaryOp: render_unary_op,
            ast.BinaryOp: render_binary_op,
            ast.Dict: render_dict,
            ast.List: render_list,
            ast.Tuple: render_tuple,
            ast.Macro: lambda: (f'%{node.name}', 0),
            ast.Reference: lambda: (f'@{node.identifier}', 0),
            ast.Call: render_call,
            ast.String: lambda: (
                repr(node),  # Add quotes.
                0,
            ),
            str: lambda: node,  # Name.
            tuple: lambda: node,  # Internal sequence, e.g. namespace path.
        }

        if type(node) in render_table:
            return render_table[type(node)]()
        else:
            # Primitive literals - expressions with precedence 0.
            return (str(node), 0)

    return '\n'.join(fold(render_node, statement) for statement in statements)


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
                identifier=make_identifier(['hyperion', 'gin'], '_eval_unary'),
                arguments=[
                    ('op', ast.String(node.operator)),
                    ('v', node.operand),
                ]
            )

        if type(node) is ast.BinaryOp:
            return ast.Call(
                identifier=make_identifier(['hyperion', 'gin'], '_eval_binary'),
                arguments=[
                    ('l', node.left),
                    ('op', ast.String(node.operator)),
                    ('r', node.right),
                ]
            )

        return node

    return [fold(convert_node, statement) for statement in statements]


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


def preprocess_config(statements):
    statements = expressions_to_calls(statements)
    return calls_to_evaluated_references(statements)
