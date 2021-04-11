import collections
import functools
import operator

import hypothesis as ht
from hypothesis import strategies as st
import pytest

from hyperion import ast
from hyperion import sweeps
from hyperion import testing
from hyperion import transforms


def st_sweeps(allow_empty=True):
    min_size = 0 if allow_empty else 1
    return st.lists(
        st.dictionaries(
            keys=st.integers(),
            values=st.integers(),
        ),
        min_size=min_size,
    )


def sweep_lists(allow_empty=True):
    return st.lists(st_sweeps(allow_empty), max_size=4)


@ht.given(st.integers(), st.integers())
def test_singleton_equals_all_of_one_value(name, value):
    assert list(sweeps.singleton(name, value)) == list(sweeps.all(name, [value]))


@ht.given(st.integers(), st.sets(st.integers()))
def test_all_produces_all_values_with_specified_name(name, values):
    sweep = list(sweeps.all(name, values))
    assert len(sweep) == len(values)
    assert all(list(config_dict.keys()) == [name] for config_dict in sweep)
    assert all(set(config_dict.values()) <= values for config_dict in sweep)


@pytest.mark.parametrize(
    "sweep_operator,identity",
    [
        (sweeps.union, sweeps.void),
        (sweeps.product, sweeps.unit),
    ],
)
@ht.given(st_sweeps())
def test_identity(sweep_operator, identity, sweep):
    assert list(sweep_operator(identity(), sweep)) == sweep
    assert list(sweep_operator(sweep, identity())) == sweep


@pytest.mark.parametrize(
    "sweep_operator,card_operator,card_identity",
    [
        (sweeps.union, operator.add, 0),
        (sweeps.product, operator.mul, 1),
    ],
)
@ht.given(sweep_lists())
def test_cardinality(sweep_operator, card_operator, card_identity, sweep_list):
    expected_card = functools.reduce(card_operator, map(len, sweep_list), card_identity)
    actual_card = len(list(sweep_operator(*sweep_list)))
    assert actual_card == expected_card


def freeze_config_dict(config_dict):
    return tuple(sorted(config_dict.items()))


def freeze_sweep(sweep):
    return set(map(freeze_config_dict, sweep))


@ht.given(sweep_lists())
def test_union_completeness(sweep_list):
    frozen_union_sweep = freeze_sweep(sweeps.union(*sweep_list))
    for sweep in sweep_list:
        for config_dict in sweep:
            assert freeze_config_dict(config_dict) in frozen_union_sweep


def unique_config_dicts(sweep_list):
    for sweep in sweep_list:
        if len(freeze_sweep(sweep)) != len(sweep):
            return False

    return True


def disjoint_names(sweep_list):
    name_sets = [
        {name for config_dict in sweep for name in config_dict.keys()}
        for sweep in sweep_list
    ]
    names_so_far = set()
    for name_set in name_sets:
        for name in name_set:
            if name in names_so_far:
                return False
        names_so_far |= name_set

    return True


@ht.given(sweep_lists().filter(unique_config_dicts).filter(disjoint_names))
def test_product_uniqueness(sweep_list):
    product_sweep = list(sweeps.product(*sweep_list))
    assert len(product_sweep) == len(freeze_sweep(product_sweep))


@ht.given(sweep_lists(allow_empty=False).filter(disjoint_names))
def test_product_completeness(sweep_list):
    product_sweep = sweeps.product(*sweep_list)
    name_to_values = collections.defaultdict(set)
    for config_dict in product_sweep:
        for (name, value) in config_dict.items():
            name_to_values[name].add(value)

    for sweep in sweep_list:
        for config_dict in sweep:
            for (name, value) in config_dict.items():
                assert value in name_to_values[name]


def test_empty_table_equals_void():
    assert list(sweeps.table(names=[], value_seqs=[])) == list(sweeps.void())


@ht.given(st.integers(), st.lists(st.integers()))
def test_single_column_table_equals_all(name, values):
    assert list(sweeps.table([name], [[value] for value in values])) == list(
        sweeps.all(name, values)
    )


@ht.given(st.data(), st.lists(st.integers(), min_size=1))
def test_table_equals_union_of_products_of_singletons(data, names):
    value_seqs = data.draw(st.lists(st.tuples(*([st.integers()] * len(names)))))

    table = sweeps.table(names, value_seqs)
    union = sweeps.union(
        *[
            sweeps.product(
                *[
                    sweeps.singleton(name, value)
                    for (name, value) in zip(names, value_seq)
                ]
            )
            for value_seq in value_seqs
        ]
    )

    assert list(table) == list(union)


@ht.settings(deadline=500)
@ht.given(testing.sweeps(with_imports=False, with_includes=False))
def test_generate_configs_produces_gin_parsable_output(sweep):
    preprocessed_sweep = transforms.preprocess_sweep(sweep, with_partial_eval=False)
    for config in sweeps.generate_configs(preprocessed_sweep):
        testing.try_to_parse_config_using_gin(config)
