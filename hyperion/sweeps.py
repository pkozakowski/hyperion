def unit():
    return [{}]


def all(name, values):
    return [{name: value} for value in values]


def product(*sweeps):
    if not sweeps:
        return unit()

    (first, *rest) = *sweeps
    second = product(*rest)
    return [
        dict(**first_hparams, **second_hparams)
        for first_hparams in first
        for second_hparams in second
    ]


def union(*sweeps):
    return [hparams for sweep in sweeps for hparams in sweep]
