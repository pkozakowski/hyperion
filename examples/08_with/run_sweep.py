#!/usr/bin/env python


import gin
import hyperion

import trainer


print("flat:")
for config in hyperion.parse_sweep_file("flat.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()

print("nested:")
for config in hyperion.parse_sweep_file("nested.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()

print("composability:")
for config in hyperion.parse_sweep_file("composability.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()
