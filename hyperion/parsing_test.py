import hypothesis as ht
from hypothesis import strategies as st

from hyperion import parsing
from hyperion import rendering
from hyperion import testing


settings = {
    # Disable the shrinking phase - it's really slow for parsing.
    "phases": (ht.Phase.explicit, ht.Phase.reuse, ht.Phase.generate, ht.Phase.target),
    # Extend the deadline to fit more complex trees.
    "deadline": 500,
    # Lower the number of examples to match.
    "max_examples": 50,
}


@ht.settings(**settings)
@ht.given(testing.configs())
def test_parse_config_inverses_render(original_config):
    text = rendering.render(original_config)
    ht.note(f"Rendered config: {text}")
    parsed_config = parsing.parse_config(text)
    assert parsed_config == original_config


@ht.settings(**settings)
@ht.given(testing.sweeps())
def test_parse_sweep_inverses_render(original_sweep):
    text = rendering.render(original_sweep)
    ht.note(f"Rendered sweep: {text}")
    parsed_sweep = parsing.parse_sweep(text)
    assert parsed_sweep == original_sweep


@ht.settings(**settings)
@ht.given(testing.configs())
def test_configs_are_sweeps(config):
    text = rendering.render(config)
    ht.note(f"Rendered config: {text}")
    parsed_sweep = parsing.parse_sweep(text)
    assert parsed_sweep.statements == config.statements
