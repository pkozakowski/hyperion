#!/usr/bin/env python


import gin
import hyperion

import trainer


print("table:")
for config in hyperion.parse_sweep_file("table.hyp"):
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
