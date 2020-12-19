def singleton(name, value):
    yield {name: value}


def all(name, values):
    for value in values:
        yield from singleton(name, value)


def unit():
    yield {}


def void():
    return
    yield


def product(*sweeps):
    if not sweeps:
        yield from unit()
        return

    (first, *rest) = sweeps
    second = list(product(*rest))
    for first_hparams in first:
        for second_hparams in second:
            all_hparams = first_hparams.copy()
            all_hparams.update(second_hparams)
            yield all_hparams


def union(*sweeps):
    for sweep in sweeps:
        yield from sweep


def table(names, value_seqs):
    for value_seq in value_seqs:
        assert len(value_seq) == len(names)
        yield dict(zip(names, value_seq))
