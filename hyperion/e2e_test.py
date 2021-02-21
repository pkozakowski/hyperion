import contextlib
import functools
import operator
import os
import string
import sys

import hypothesis as ht
from hypothesis import strategies as st
import pytest

from hyperion import ast
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


configurable_module_name = "_configurables"


def _unload_configurables():
    if configurable_module_name in sys.modules:
        del sys.modules[configurable_module_name]


def _try_to_parse_config(parse_fn, config_to_register=None):
    _unload_configurables()

    with testing.try_in_gin_sandbox(config_to_register) as gin:
        runtime.register(gin)
        e2e.register(gin)
        with testing.try_with_eval():
            parse_fn()


def _try_to_parse_sweep_configs(config_stream, sweep_to_register=None):
    with testing.try_with_eval():
        _unload_configurables()

        for rendered_config in config_stream:
            ht.note(f"Rendered config: {rendered_config}")
            with testing.try_in_gin_sandbox(sweep_to_register) as gin:
                runtime.register(gin)
                e2e.register(gin)
                gin.parse_config(rendered_config)

            _unload_configurables()


def _render_to_file(config_or_sweep, tmpdir_factory):
    rendered = rendering.render(config_or_sweep)
    path = str(tmpdir_factory.mktemp("tmp").join("config_or_sweep"))
    with open(path, "w") as f:
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


def _extra_config_to_file(config, tmpdir_factory):
    config_with_extra = transforms.calls_to_evaluated_references(config)
    original_bindings = config_with_extra.statements[: len(config.statements)]
    original_config = config._replace(statements=original_bindings)
    extra_config = ast.Config(
        statements=config_with_extra.statements[len(config.statements) :]
    )

    rendered_original_config = rendering.render(original_config)
    ht.note(f"Original config:\n{rendered_original_config}\n")
    rendered_extra_config = rendering.render(extra_config)
    ht.note(f"Extra config:\n{rendered_extra_config}\n")

    extra_config_path = _render_to_file(extra_config, tmpdir_factory)
    return (extra_config_path, original_config)


def _add_prelude(config, tmpdir_factory):
    (extra_config_path, original_config) = _extra_config_to_file(config, tmpdir_factory)

    tmpdir = tmpdir_factory.mktemp("tmp")
    module_path = str(tmpdir.join(configurable_module_name + ".py"))
    testing.save_used_configurables_as_module(config, module_path)

    config = original_config._replace(
        statements=(
            (
                ast.Import(namespace=ast.Namespace(path=(configurable_module_name,))),
                ast.Include(path=ast.String(extra_config_path)),
            )
            + original_config.statements
        )
    )
    return (config, str(tmpdir))


@contextlib.contextmanager
def _python_path(path):
    sys.path.append(path)
    try:
        yield
    finally:
        sys.path.pop()


# TODO: Test:
# - that bindings get correct values (just static); 2 variants:
#   - standalone
#   - with an include and an import (as before)
# - parse_sweep*_produces_different_configs
#   - assert len(set(rendered_configs)) == len(set(preprocessed_configs))


@ht.settings(**settings)
@ht.given(configs_without_prelude)
def test_parse_config_succeeds_without_prelude(config):
    rendered_config = rendering.render(config)
    _try_to_parse_config(lambda: e2e.parse_config(rendered_config), config)


@ht.settings(**settings)
@ht.given(configs_without_prelude)
def test_parse_config_succeeds_with_prelude(tmpdir_factory, config):
    (config, tmpdir) = _add_prelude(config, tmpdir_factory)
    rendered_config = rendering.render(config)
    with _python_path(tmpdir):
        _try_to_parse_config(lambda: e2e.parse_config(rendered_config))


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_succeeds_without_prelude(sweep):
    rendered_sweep = rendering.render(sweep)
    _try_to_parse_sweep_configs(e2e.parse_sweep(rendered_sweep), sweep)


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_succeeds_with_prelude(tmpdir_factory, sweep):
    (sweep, tmpdir) = _add_prelude(sweep, tmpdir_factory)
    rendered_sweep = rendering.render(sweep)
    with _python_path(tmpdir):
        _try_to_parse_sweep_configs(e2e.parse_sweep(rendered_sweep))


@ht.settings(**settings)
@ht.given(configs_without_prelude)
def test_parse_config_file_succeeds_without_prelude(tmpdir_factory, config):
    path = _render_to_file(config, tmpdir_factory)
    _try_to_parse_config(lambda: e2e.parse_config_file(path), config)


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_file_succeeds_without_prelude(tmpdir_factory, sweep):
    path = _render_to_file(sweep, tmpdir_factory)
    _try_to_parse_sweep_configs(e2e.parse_sweep_file(path), sweep)


@ht.settings(**settings)
@_given_file_paths_and_text(configs_without_prelude)
def test_parse_config_files_and_bindings_succeeds_without_prelude(
    paths, text, merged_config
):
    _try_to_parse_config(
        lambda: e2e.parse_config_files_and_bindings(bindings=text, config_files=paths),
        merged_config,
    )


@ht.settings(**settings)
@_given_file_paths_and_text(sweeps_without_prelude)
def test_parse_sweep_files_and_bindings_succeeds_without_prelude(
    paths, text, merged_sweep
):
    _try_to_parse_sweep_configs(
        e2e.parse_sweep_files_and_bindings(bindings=text, sweep_files=paths),
        merged_sweep,
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
