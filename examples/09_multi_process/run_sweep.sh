#!/usr/bin/env bash


hyperion sweep.hyp configs/

for config in configs/sweep_*.gin; do
    python trainer.py $config
    echo
done
