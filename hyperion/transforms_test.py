import hypothesis
import pytest

from hyperion import ast
from hyperion import rendering
from hyperion import testing
from hyperion import transforms


def _test_idempotence(transform, original):
    transformed_once = transform(original)
    transformed_twice = transform(transformed_once)
    assert transformed_once == transformed_twice


def _test_partial_idempotence(transform, original):
    try:
        _test_idempotence(transform, original)
    except Exception as e:
        if type(e) not in testing.allowed_eval_exceptions:
            raise


@pytest.mark.parametrize(
    "transform",
    (
        transforms.expressions_to_calls,
        transforms.calls_to_evaluated_references,
    ),
)
@hypothesis.given(testing.configs())
def test_config_idempotence(transform, config):
    _test_idempotence(transform, config)


@pytest.mark.parametrize(
    "transform",
    (
        transforms.partial_eval,
        transforms.preprocess_config,
    ),
)
@hypothesis.given(testing.configs())
def test_config_partial_idempotence(transform, config):
    _test_partial_idempotence(transform, config)


@hypothesis.given(testing.configs(with_imports=False))
def test_preprocess_config_produces_gin_parsable_output(config):
    try:
        preprocessed_config = transforms.preprocess_config(config)
    except Exception as e:
        if type(e) in testing.allowed_eval_exceptions:
            return

    rendered_config = rendering.render(preprocessed_config)
    hypothesis.note(f"Rendered config: {rendered_config}")

    with testing.gin_sandbox() as gin:
        testing.register_used_configurables(gin, preprocessed_config)

        try:
            gin.parse_config(rendered_config)
        except TypeError as e:
            # The only exception we allow here, for cases like {[]: ...}.
            if "unhashable type" not in str(e):
                raise


@pytest.mark.filterwarnings("ignore::SyntaxWarning")
@hypothesis.given(testing.exprs(for_eval=True))
def test_partial_eval_equals_python_eval(expr):
    (rendered_expr, _) = rendering.render(expr)
    hypothesis.note(f"Rendered expr: {rendered_expr}")
    expected_exc = None
    try:
        expected_value = eval(rendered_expr, {}, {})
    except Exception as e:
        if type(e) in testing.allowed_eval_exceptions:
            expected_exc = e
        else:
            raise

    try:
        actual_value = transforms.partial_eval(expr)
    except Exception as actual_exc:
        testing.assert_exception_equal(actual_exc, expected_exc)
    else:
        assert not expected_exc and actual_value == expected_value


@hypothesis.given(testing.sweeps())
def test_validate_sweep_accepts_valid_sweeps(sweep):
    transforms.validate_sweep(sweep)


def has_blocks(sweep):
    return any(
        type(statement) in (ast.Product, ast.Union) for statement in sweep.statements
    )


@hypothesis.given(
    testing.sweeps(leaf_sts=[testing.imports()], allow_empty=False).filter(has_blocks)
)
def test_validate_sweep_raises_on_nested_imports(sweep):
    with pytest.raises(ValueError):
        transforms.validate_sweep(sweep)


@hypothesis.given(
    testing.sweeps(leaf_sts=[testing.tables(correct=False)], allow_empty=False).filter(
        has_blocks
    )
)
def test_validate_sweep_raises_on_incorrect_tables(sweep):
    with pytest.raises(ValueError):
        transforms.validate_sweep(sweep)


@pytest.mark.parametrize(
    "transform",
    (transforms.bindings_to_singletons,),
)
@hypothesis.given(testing.sweeps())
def test_sweep_idempotence(transform, sweep):
    _test_idempotence(transform, sweep)


@pytest.mark.parametrize(
    "transform",
    (
        transforms.validate_sweep,
        transforms.preprocess_sweep,
    ),
)
@hypothesis.given(testing.sweeps())
def test_sweep_partial_idempotence(transform, sweep):
    _test_partial_idempotence(transform, sweep)


@hypothesis.given(testing.sweeps(with_bindings=False))
def test_bindings_to_singletons_is_identity_without_bindings(sweep):
    transformed_sweep = transforms.bindings_to_singletons(sweep)
    assert transformed_sweep == sweep


@hypothesis.given(testing.sweeps())
def test_bindings_to_singletons_removes_bindings(sweep):
    transformed_sweep = transforms.bindings_to_singletons(sweep)

    def fail_on_binding(node):
        if type(node) is ast.Binding:
            pytest.fail()

    transforms.fold(fail_on_binding, transformed_sweep)
