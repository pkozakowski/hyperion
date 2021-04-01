from hyperion import transforms


def eval_unary_op(o, v):
    return transforms.eval_unary_op(operator=o, operand=v)


def eval_binary_op(l, o, r):
    return transforms.eval_binary_op(left=l, operator=o, right=r)


def register(gin):
    # Use short names to minimize the generated configs.
    gin.external_configurable(eval_unary_op, name="_u", module="_h")
    gin.external_configurable(eval_binary_op, name="_b", module="_h")
