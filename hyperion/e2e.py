import io
import os

import gin
from gin import config as gin_config

from hyperion import parsing
from hyperion import rendering
from hyperion import sweeps
from hyperion import transforms


def _preprocess_bindings(bindings):
    if type(bindings) in (list, tuple):
        bindings = "\n".join(bindings)
    return bindings


def _hyperion_to_gin(text, is_config=True):
    text = _preprocess_bindings(text)
    tree = parsing.parse_config(text)
    if is_config:
        tree = transforms.preprocess_config(tree)
    return rendering.render(tree)


def _hyperion_to_gin_open(path):
    with open(path, "r") as f:
        bindings = _hyperion_to_gin(f.read())
        return io.StringIO(bindings)


def register(gin):
    # Override the default file reader with our own. We need to access a private
    # member of the module, because Gin API doesn't allow this.
    gin.config._FILE_READERS = [(_hyperion_to_gin_open, os.path.isfile)]


register(gin)


# Implementation of the Gin API:
# ==============================


def parse_config(bindings, skip_unknown=False):
    gin_bindings = _hyperion_to_gin(bindings)
    return gin.parse_config(gin_bindings, skip_unknown=skip_unknown)


# With the default file reader overridden, we can use gin.parse_config_file.
parse_config_file = gin.parse_config_file


def parse_config_files_and_bindings(
    config_files=None,
    bindings=None,
    finalize_config=True,
    skip_unknown=False,
    print_includes_and_imports=False,
):
    if bindings is None:
        bindings = ""

    gin_bindings = _hyperion_to_gin(bindings)
    return gin.parse_config_files_and_bindings(
        config_files=config_files,
        bindings=bindings,
        finalize_config=finalize_config,
        skip_unknown=skip_unknown,
        print_includes_and_imports=print_includes_and_imports,
    )


def parse_value(value):
    gin_value = _hyperion_to_gin(value, is_config=False)
    return gin.parse_value(gin_value)


# Implementation of the Hyperion sweep API:
# =========================================


def parse_sweep(bindings):
    bindings = _preprocess_bindings(bindings)
    sweep = parsing.parse_sweep(bindings)
    sweep = transforms.preprocess_sweep(sweep)
    (sweep, prelude) = transforms.remove_prelude(sweep)
    for config in sweeps.generate_configs(sweep):
        config = config._replace(statements=(prelude + config.statements))
        yield rendering.render(config)


def parse_sweep_file(sweep_file):
    with open(sweep_file, "r") as f:
        yield from parse_sweep(f.read())


def parse_sweep_files_and_bindings(sweep_files=(), bindings=""):
    def read_file(path):
        with open(path, "r") as f:
            return f.read()

    bindings = "\n".join(
        list(map(read_file, sweep_files)) + [_preprocess_bindings(bindings)]
    )
    yield from parse_sweep(bindings)
