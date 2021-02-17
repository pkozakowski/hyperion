import functools
import operator
import os

import hypothesis as ht
from hypothesis import strategies as st
import pytest

from hyperion import e2e
from hyperion import rendering
from hyperion import runtime
from hyperion import testing
from hyperion import transforms


settings = {
    # Disable the shrinking phase - it's really slow for parsing.
    "phases": (ht.Phase.explicit, ht.Phase.reuse, ht.Phase.generate, ht.Phase.target),
    # Extend the deadline to fit more complex trees.
    "deadline": 500,
    # These tests just check the plumbing - we don't need that many examples.
    "max_examples": 10,
}


configs_without_prelude = testing.configs(with_imports=False, with_includes=False)
sweeps_without_prelude = testing.sweeps(with_imports=False, with_includes=False)


def _try_to_parse_config(config, parse_fn):
    with testing.try_in_gin_sandbox(config) as gin:
        runtime.register(gin)
        e2e.register(gin)
        with testing.try_with_eval():
            parse_fn()


def _try_to_parse_sweep_configs(sweep, config_stream):
    with testing.try_with_eval():
        for rendered_config in config_stream:
            ht.note(f"Rendered config: {rendered_config}")
            with testing.try_in_gin_sandbox(sweep) as gin:
                runtime.register(gin)
                e2e.register(gin)
                gin.parse_config(rendered_config)


def _render_to_file(config_or_sweep, tmpdir_factory):
    rendered = rendering.render(config_or_sweep)
    path = str(tmpdir_factory.mktemp("tmp").join("config_or_sweep"))
    with open(path, 'w') as f:
        f.write(rendered)
    return path


def _merge_configs_or_sweeps(configs_or_sweeps):
    return configs_or_sweeps[0]._replace(
        statements=functools.reduce(
            operator.add, [x.statements for x in configs_or_sweeps]
        )
    )


def _given_file_paths_and_text(configs_or_sweeps):
    def decorator(f):
        def decorated(tmpdir_factory, file_configs, text_config):
            paths = [_render_to_file(config, tmpdir_factory) for config in file_configs]
            text = rendering.render(text_config) if text_config else None
            configs = file_configs + ([text_config] if text_config else [])
            if configs:
                merged_config = _merge_configs_or_sweeps(configs)
            else:
                merged_config = None

            f(paths, text, merged_config)

        return ht.given(
            st.lists(configs_without_prelude, max_size=2),
            st.one_of(st.none(), configs_without_prelude),
        )(decorated)

    return decorator


# TODO: Test:
# - parse_{config,sweep}_succeeds_with_prelude using:
#   - a predefined include: put all bindings there
#   - a predefined import: put all used configurables there
# - that bindings get correct values (just static); 2 variants:
#   - standalone
#   - with an include and an import (as before)


@ht.settings(**settings)
@ht.given(configs_without_prelude)
def test_parse_config_succeeds_without_prelude(config):
    text = rendering.render(config)
    _try_to_parse_config(config, lambda: e2e.parse_config(text))


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_succeeds_without_prelude(sweep):
    rendered_sweep = rendering.render(sweep)
    _try_to_parse_sweep_configs(sweep, e2e.parse_sweep(rendered_sweep))


@ht.settings(**settings)
@ht.given(configs_without_prelude)
def test_parse_config_file_succeeds_without_prelude(tmpdir_factory, config):
    path = _render_to_file(config, tmpdir_factory)
    _try_to_parse_config(config, lambda: e2e.parse_config_file(path))


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_file_succeeds_without_prelude(tmpdir_factory, sweep):
    path = _render_to_file(sweep, tmpdir_factory)
    _try_to_parse_sweep_configs(sweep, e2e.parse_sweep_file(path))


@ht.settings(**settings)
@_given_file_paths_and_text(configs_without_prelude)
def test_parse_config_files_and_bindings_succeeds_without_prelude(
    paths, text, merged_config
):
    _try_to_parse_config(
        merged_config,
        lambda: e2e.parse_config_files_and_bindings(bindings=text, config_files=paths),
    )


@ht.settings(**settings)
@_given_file_paths_and_text(sweeps_without_prelude)
def test_parse_sweep_files_and_bindings_succeeds_without_prelude(
    paths, text, merged_config
):
    _try_to_parse_sweep_configs(
        merged_config,
        e2e.parse_sweep_files_and_bindings(bindings=text, sweep_files=paths),
    )


@ht.settings(**settings)
@ht.given(testing.exprs(for_eval=True))
def test_parse_value_evaluates_exprs(expr):
    (rendered_expr, _) = rendering.render(expr)
    ht.note(f"Rendered expr: {rendered_expr}")

    expected_exc = None
    try:
        expected_value = transforms.partial_eval(expr)
    except Exception as e:
        if type(e) in testing.allowed_eval_exceptions:
            expected_exc = e
        else:
            raise

    try:
        with testing.try_in_gin_sandbox(expr) as gin:
            e2e.register(gin)
            actual_value = e2e.parse_value(rendered_expr)
    except Exception as actual_exc:
        testing.assert_exception_equal(actual_exc, expected_exc)
    else:
        assert not expected_exc and actual_value == expected_value
