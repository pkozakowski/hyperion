import hypothesis
from hypothesis import strategies as st

from hyperion import parsing
from hyperion import rendering
from hyperion import testing


@hypothesis.given(testing.configs())
def test_parse_config_inverses_render(original_config):
    text = rendering.render(original_config)
    hypothesis.note(f"Rendered config: {text}")
    parsed_config = parsing.parse_config(text)
    assert parsed_config == original_config
