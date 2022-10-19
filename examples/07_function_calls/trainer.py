#!/usr/bin/env python


import math

import gin


@gin.configurable
class Transformer:
    def __init__(self, d_model, d_ff, n_heads, n_layers):
        print("model parameters:", locals())

    # Model code...


@gin.configurable
def compute_learning_rate(base, batch_size):
    # Learning rate scaling according to https://arxiv.org/pdf/1404.5997.pdf.
    return base * math.sqrt(batch_size)


@gin.configurable
def train(model_class, learning_rate, n_steps):
    model = model_class()
    print("training parameters:", locals())


if __name__ == "__main__":
    gin.parse_config_file("config.gin")
    train()
