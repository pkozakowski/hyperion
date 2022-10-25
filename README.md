# Hyperion: hyperparameter sweeps on steroids

 [![build status](https://circleci.com/gh/pkozakowski/hyperion.svg?style=shield&circle-token=e18760f1e3e06bc3f4bec958ba889731e6b023bc)](https://circleci.com/gh/pkozakowski/hyperion) [![code coverage](https://img.shields.io/codecov/c/gh/pkozakowski/hyperion?token=9GH4LLWWJI)](https://codecov.io/gh/pkozakowski/hyperion) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/pkozakowski/hyperion/blob/main/LICENSE) [![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Have you used [Gin Config](https://github.com/google/gin-config)? If not, I encourage you to try it! It allows you to configure your Python ML experiments in a simple and intuitive way.

Suppose you have an ML experiment like:

```python
# 01_gin/trainer.py

import gin

@gin.configurable
class Transformer:
    def __init__(self, d_model, d_ff, n_layers, dropout):
        # ...

    # Model code...

@gin.configurable
def train(model_class, learning_rate, n_steps):
    model = model_class()
    # Training code...

# ...
```

Then you can create a configuration file like this:

```python
# 01_gin/my_transformer.gin

Transformer.d_model = 1024
Transformer.d_ff = 4096
Transformer.n_layers = 6
Transformer.dropout = 0.1

train.model_class = @Transformer
train.learning_rate = 0.001
train.n_steps = 100000
```

Feed the config to Gin:

```python
# 01_gin/trainer.py

# ...

if __name__ == '__main__':
    gin.parse_config_file('my_transformer.gin')
    train()
```

... and it will forward all your hyperparameters to the appropriate functions automagically!

However, one thing that Gin cannot do is define hyperparameter sweeps. If you want to run a search over different hyperparameter values, you need to write your own loops and override the Gin configs manually, which can lead to messy and hard-to-debug code.

That's where Hyperion comes in! This tool allows you to define hyperparameter sweeps using a syntax similar to Gin. It also introduces new features for writing configs, including [expressions](#expressions).

To install, run:

```bash
pip install https://github.com/pkozakowski/hyperion/releases/download/v0.1.0/hyperion-0.1.0-py3-none-any.whl
```

## Hyperparameter sweeps

Let's say you want to tune the dimensionality of the above model. Hyperion makes it easy:

```python
# 02_one_param_sweep/sweep.hyp

include 'my_transformer.gin'  # Load the base config.

Transformer.d_model: [512, 1024, 2048]
```

Then load the sweep file in Hyperion:

```python
# 02_one_param_sweep/run_sweep.py

import gin
import hyperion

import trainer

for config in hyperion.parse_sweep_file('sweep.hyp'):
    gin.parse_config(config)
    trainer.train()
```

... and that's it! Hyperion will generate config files you can pass to Gin.

In a [later section](#running-experiments-in-separate-processes) we'll see how to run experiments in different processes.

The examples shown here are also available in the `examples/` directory.

### Grid searches

Now let's say we want to tune both `d_model` and `n_layers` in a grid search:

```python
# 03_grid_search/sweep.hyp

include 'my_transformer.gin'

Transformer.d_model: [512, 1024, 2048]
Transformer.n_layers: [4, 6, 8, 10]
```

Hyperion will generate all combinations of the two hyperparameters and output the Gin configs, which you can load the same way as before.

But that's not all - Hyperion can handle much more complex setups.

### Unions and products

Grid searches are great, but their sizes can blow up quite quickly. Also, some hyperparameters may depend on one another. Sometimes instead of making one big grid search it's better to run a couple of smaller grids. That's where the `union` and `product` blocks come in.

Say that you want to also tune `d_ff`, but you don't want to make your model too big. You can split your grid into parts with different hyperparameter ranges for each value of `d_ff`:

```python
# 04_union_product/union_of_products.hyp

include 'my_transformer.gin'

union:
    product:
        Transformer.d_ff = 2048
        Transformer.d_model: [512, 1024, 2048]
        Transformer.n_layers: [4, 6, 8, 10]

    product:
        Transformer.d_ff = 4096
        Transformer.d_model: [512, 1024, 2048]
        Transformer.n_layers: [4, 6, 8]  # Limit the number of layers.

    product:
        Transformer.d_ff = 8192
        Transformer.d_model: [512, 1024] # Limit d_model too.
        Transformer.n_layers: [4, 6, 8]
```

Hyperion defines a sweep as a set $S$ of possible hyperparameter configs. The `union` block computes a union over sets: $S = S_1 | S_2 | \ldots$. The `product` block computes a Cartesian product: $S = S_1 \times S_2 \times \ldots$.

The sweep resides in an implicit `product` block, so sweeps

```python
# 04_union_product/implicit_product.hyp

include 'my_transformer.gin'

Transformer.d_model: [512, 1024, 2048]
Transformer.n_layers: [4, 6, 8, 10]
```

and

```python
# 04_union_product/explicit_product.hyp

include 'my_transformer.gin'

product:
    Transformer.d_model: [512, 1024, 2048]
    Transformer.n_layers: [4, 6, 8, 10]
```

are equivalent.

`union` and `product` blocks are composable, so you can do things like:

```python
# 04_union_product/composability.hyp

include 'my_transformer.gin'

product:
    Transformer.n_layers: [4, 6, 8, 10]

    union:
        Transformer.d_model: [512, 1024, 2048]
        Transformer.d_ff: [2048, 4096, 8192]
```

### Tables

What if you just want to list the hyperparameter settings that should be run? Tables let you write them very succintly:

```python
# 05_table/table.hyp

include 'my_transformer.gin'

table (Transformer.d_model, Transformer.d_ff, Transformer.n_layers):
    512, 2048, 4
    1024, 4096, 6
    2048, 8192, 8
```

And they compose with `product` and `union`, so for instance

```python
# 05_table/composability.hyp

include 'my_transformer.gin'

product:
    table (Transformer.d_model, Transformer.d_ff, Transformer.n_layers):
        512, 2048, 4
        1024, 4096, 6
        2048, 8192, 8

    Transformer.n_heads: [2, 4, 8]
```

will run the 3 numbers of heads for every row of the table.

### Expressions

Hyperion implements a reasonable subset of the Python expression language. This is ueful for instance when you want to compute one hyperparameter based on another one.

Suppose you want to tune `d_model` and set `d_ff` to be 4 times that value. Normally you'd have to list those settings manually in a table, but with expressions and Gin macros you can just:

```python
# examples/06_expressions/one_param_sweep.hyp

include 'my_transformer.gin'

d_model: [512, 1024, 2048]

Transformer.d_model = %d_model
Transformer.d_ff = %d_model * 4
```

Of course you can tune the multiplier too:

```python
# examples/06_expressions/two_param_sweep.hyp

include 'my_transformer.gin'

d_model: [512, 1024, 2048]
d_ff_mul: [1, 2, 4]

Transformer.d_model = %d_model
Transformer.d_ff = %d_model * %d_ff_mul
```

### Function calls

Gin supports calling Python functions from the configs:

```python
# 07_function_calls/trainer.py

import math

import gin

# ...

@gin.configurable
def compute_learning_rate(base, batch_size):
    # Learning rate scaling according to https://arxiv.org/pdf/1404.5997.pdf.
    return base * math.sqrt(batch_size)

@gin.configurable
def train(model_class, learning_rate, n_steps):
    model = model_class()
    # Training code...

# ...
```

But you have to supply the arguments of the call as separate bindings:

```python
# 07_function_calls/config.gin

include 'my_transformer.gin'

compute_learning_rate.base = 0.001
compute_learning_rate.batch_size = 64

train.learning_rate = @compute_learning_rate()
```

This looks a bit weird and can become cumbersome when you have multiple calls to the same function.

Hyperion allows you to supply the arguments in the call itself:

```python
# 07_function_calls/sweep.hyp

include 'my_transformer.gin'

batch_size: [64, 128, 256]

train.learning_rate = @compute_learning_rate(base=0.001, batch_size=%batch_size)
```

### `with` blocks

You might have noticed that the sweeps we've written so far were a bit redundant. For instance, in

```python
# 08_with/flat.hyp

include 'my_transformer.gin'

Transformer.d_model: [512, 1024, 2048]
Transformer.n_layers: [4, 6, 8, 10]
```

the `Transformer.` part occurs in multiple lines. You can shorten this using `with` blocks:

```python
# 08_with/nested.hyp

include 'my_transformer.gin'

with Transformer:
    d_model: [512, 1024, 2048]
    n_layers: [4, 6, 8, 10]
```

They compose with the other block types, for instance:

```python
# 08_with/composability.hyp

include 'my_transformer.gin'

with Transformer:
    union:
        table (d_model, d_ff, n_layers):
            512, 2048, 4
            1024, 4096, 6
            2048, 8192, 8

        n_heads: [2, 4, 8]
```

## Running experiments in separate processes

In practical scenarios, you'll probably want to run your experiments in different processes, possibly on different machines, in a cluster job queue or in a cloud. You can use the Hyperion CLI to generate configs and save them to files, and then forward them to the training processes.

You'll need a training script which can receive a config file as an argument:

```python
# 09_multi_process/trainer.py

import sys

# ...

if __name__ == '__main__':
    config_path = sys.argv[1]
    gin.parse_config_file(config_path)
    train()
```

Generate configs using the `hyperion` command. The first argument is the sweep file, the second is a directory to save the configs at. For a sweep filename `sweep.hyp` they will be named `sweep_*.gin`, where `*` are consecutive numbers starting from 0.

Then lanuch the experiments.

```bash
# 09_multi_process/run_sweep.sh

hyperion sweep.hyp configs/

for config in configs/sweep_*.gin; do
    python trainer.py $config
done
```

## Gin compatibility

Hyperion aims to be a superset of the Gin configuration language, so that any Gin config is a valid Hyperion sweep containing one hyperparameter set. Conversely, Hyperion generates valid Gin configs. All of the code is thoroughly tested using the awesome package [`hypothesis`](https://hypothesis.readthedocs.io/en/latest/) to ensure this.

Some of the features of Hyperion ([expressions](#expressions), [function calls](#function-calls) and [`with` blocks](#with-blocks)) are useful for writing configs themselves. To use them in isolation from sweeps, just call the `parse_config_*` functions from the `hyperion` module instead of `gin`:

```python
# 10_config/trainer.py

import hyperion

# ...

if __name__ == '__main__':
    hyperion.parse_config_file('config.gin')
    train()
```

Then you can write configs like:

```python
# 10_config/config.gin

d_model = 2048
d_ff_mul = 4
batch_size = 64

with Transformer:
    d_model = %d_model
    d_ff = %d_model * %d_ff_mul
    n_heads = 8
    n_layers = 6

with train:
    model_class = @Transformer
    learning_rate = @compute_learning_rate(base=0.001, batch_size=%batch_size)
    n_steps = 100000
```

Note that the `@configurable` decorators should still be imported from the `gin` module.

## Citation

If you're using Hyperion in your research, please consider citing this repo:

```latex
@misc{Kozakowski2022,
  author = {Piotr Kozakowski},
  title = {Hyperion: Configuration tool for ML hyperparameter sweeps},
  year = {2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/pkozakowski/hyperion}},
}
```
