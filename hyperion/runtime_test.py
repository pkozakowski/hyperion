import hypothesis

from hyperion import ast
from hyperion import rendering
from hyperion import runtime
from hyperion import testing
from hyperion import transforms


@hypothesis.given(testing.exprs(for_eval=True))
def test_runtime_eval_equals_partial_eval(expr):
    expected_exc = None
    try:
        expected_value = transforms.partial_eval(expr)
    except Exception as e:
        if type(e) in testing.allowed_eval_exceptions:
            expected_exc = e
        else:
            raise

    def result(value):
        return value

    config = ast.Config(
        statements=(
            ast.Binding(
                identifier=transforms.make_identifier(
                    namespace_path=("result",), name="value"
                ),
                expr=expr,
            ),
        )
    )
    preprocessed_config = transforms.preprocess_config(config, with_partial_eval=False)
    rendered_config = rendering.render(preprocessed_config)
    hypothesis.note(f"Rendered config: {rendered_config}")
    with testing.gin_sandbox() as gin:
        runtime.register(gin)
        result = gin.configurable(result)
        try:
            gin.parse_config(rendered_config)
            actual_value = result()
        except Exception as actual_exc:
            testing.assert_exception_equal(actual_exc, expected_exc, from_gin=True)
        else:
            assert not expected_exc and actual_value == expected_value
