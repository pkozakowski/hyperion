import hypothesis as ht

from hyperion import e2e
from hyperion import rendering
from hyperion import runtime
from hyperion import testing

import os


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
            with testing.try_in_gin_sandbox(sweep) as gin:
                runtime.register(gin)
                e2e.register(gin)
                gin.parse_config(rendered_config)


def _render_to_file(config_or_sweep, tmpdir):
    rendered = rendering.render(config_or_sweep)
    path = os.path.join(tmpdir, 'tmp')
    with open(path, 'w') as f:
        f.write(rendered)
    return path


# TODO: Test:
# - parse_*_file*
# - parse_value: correctness (just static)
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
def test_parse_config_file_succeeds_without_prelude(tmpdir, config):
    path = _render_to_file(config, tmpdir)
    _try_to_parse_config(config, lambda: e2e.parse_config_file(path))


@ht.settings(**settings)
@ht.given(sweeps_without_prelude)
def test_parse_sweep_file_succeeds_without_prelude(tmpdir, sweep):
    path = _render_to_file(sweep, tmpdir)
    _try_to_parse_sweep_configs(path, lambda: e2e.parse_sweep_file(path))
