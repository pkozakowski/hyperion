from hyperion import ast
from hyperion import transforms


def singleton(name, value):
    yield {name: value}


def all(name, values):
    for value in values:
        yield from singleton(name, value)


def unit():
    yield {}


def void():
    return
    yield


def product(*sweeps):
    if not sweeps:
        yield from unit()
        return

    (first, *rest) = sweeps
    second = list(product(*rest))
    for first_config_dict in first:
        for second_config_dict in second:
            total_config_dict = first_config_dict.copy()
            total_config_dict.update(second_config_dict)
            yield total_config_dict


def union(*sweeps):
    for sweep in sweeps:
        yield from sweep


def table(names, value_seqs):
    for value_seq in value_seqs:
        assert len(value_seq) == len(names)
        yield dict(zip(names, value_seq))


def generate_config_dicts(sweep_tree):
    def generate_from_node(node):
        def from_product():
            return product(*node.statements)

        def from_table():
            rows = tuple(row.exprs for row in node.rows)
            return table(node.header.identifiers, rows)

        gen_map = {
            ast.All: lambda: all(*node),
            ast.Product: from_product,
            ast.Union: lambda: union(*node.statements),
            ast.Table: from_table,
            ast.Sweep: from_product,
        }
        if type(node) in gen_map:
            return gen_map[type(node)]()
        else:
            return node

    return transforms.fold(generate_from_node, sweep_tree)
