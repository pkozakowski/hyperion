import hypothesis
import pytest

from hyperion import rendering
from hyperion import testing
from hyperion import transforms


allowed_eval_exceptions = (TypeError, ValueError, ZeroDivisionError)


@pytest.mark.parametrize(
    "transform",
    (
        transforms.expressions_to_calls,
        transforms.calls_to_evaluated_references,
    ),
)
@hypothesis.given(testing.configs())
def test_idempotence(transform, config):
    transformed_once = transform(config)
    transformed_twice = transform(transformed_once)
    assert transformed_once == transformed_twice


@pytest.mark.parametrize(
    "transform",
    (
        transforms.partial_eval,
        transforms.preprocess_config,
    ),
)
@hypothesis.given(testing.configs())
def test_partial_idempotence(transform, config):
    try:
        transformed_once = transform(config)
        transformed_twice = transform(transformed_once)
        assert transformed_once == transformed_twice
    except Exception as e:
        if type(e) not in allowed_eval_exceptions:
            raise


@pytest.mark.filterwarnings("ignore::SyntaxWarning")
@hypothesis.given(testing.exprs(for_eval=True))
def test_partial_eval_equals_python_eval(expr):
    (rendered_expr, _) = rendering.render_tree(expr)
    hypothesis.note(f"Rendered expr: {rendered_expr}")
    expected_exc = None
    try:
        expected_value = eval(rendered_expr, {}, {})
    except Exception as e:
        if type(e) in allowed_eval_exceptions:
            expected_exc = e
        else:
            raise

    try:
        actual_value = transforms.partial_eval_tree(expr)
    except Exception as actual_exc:
        testing.assert_exception_equal(actual_exc, expected_exc)
    else:
        assert not expected_exc and actual_value == expected_value
