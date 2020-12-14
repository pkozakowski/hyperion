import hypothesis
from hypothesis import strategies as st

from hyperion import parser
from hyperion import testing
from hyperion import transforms


@hypothesis.given(testing.configs())
def test_parse_inverses_render(original_config):
    text = transforms.render(original_config)
    parsed_config = parser.parse_config(text)
    assert parsed_config == original_config
