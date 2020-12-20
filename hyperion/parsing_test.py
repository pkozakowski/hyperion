import hypothesis
from hypothesis import strategies as st

from hyperion import parsing
from hyperion import rendering
from hyperion import testing


max_examples = 20


@hypothesis.settings(max_examples=max_examples)
@hypothesis.given(testing.configs())
def test_parse_config_inverses_render(original_config):
    text = rendering.render(original_config)
    hypothesis.note(f"Rendered config: {text}")
    parsed_config = parsing.parse_config(text)
    assert parsed_config == original_config


@hypothesis.settings(max_examples=max_examples)
@hypothesis.given(testing.sweeps())
def test_parse_sweep_inverses_render(original_sweep):
    text = rendering.render(original_sweep)
    hypothesis.note(f"Rendered sweep: {text}")
    parsed_sweep = parsing.parse_sweep(text)
    assert parsed_sweep == original_sweep
