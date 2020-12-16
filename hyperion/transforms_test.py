import hypothesis
import pytest

from hyperion import testing
from hyperion import transforms


@pytest.mark.parametrize(
    "transform",
    (
        transforms.expressions_to_calls,
        transforms.calls_to_evaluated_references,
        transforms.preprocess_config,
    ),
)
@hypothesis.given(testing.configs())
def test_idempotence(transform, config):
    transformed_once = transforms.expressions_to_calls(config)
    transformed_twice = transforms.expressions_to_calls(transformed_once)
    assert transformed_once == transformed_twice
