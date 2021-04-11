import io
import os

import gin as gin_module

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
    global gin_module
    gin_module = gin

    # Override the default file reader with our own. We need to access a private
    # member of the module, because Gin API doesn't allow this.
    gin_module.config._FILE_READERS = [(_hyperion_to_gin_open, os.path.isfile)]


register(gin_module)


# Implementation of the Gin API:
# ==============================


def parse_config(bindings, skip_unknown=False):
    gin_bindings = _hyperion_to_gin(bindings)
    return gin_module.parse_config(gin_bindings, skip_unknown=skip_unknown)


# With the default file reader overridden, we can use gin_module.parse_config_file.
def parse_config_file(config_file):
    return gin_module.parse_config_file(config_file)


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
    return gin_module.parse_config_files_and_bindings(
        config_files=config_files,
        bindings=gin_bindings,
        finalize_config=finalize_config,
        skip_unknown=skip_unknown,
        print_includes_and_imports=print_includes_and_imports,
    )


def parse_value(value):
    f = gin_module.external_configurable(lambda x: x, name="_f")
    binding = f"_f.x = {value}"
    gin_binding = _hyperion_to_gin(binding, is_config=True)
    with gin_module.unlock_config():
        gin_module.parse_config(gin_binding)
    return f()


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
