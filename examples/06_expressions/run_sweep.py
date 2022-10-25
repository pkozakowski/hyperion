#!/usr/bin/env python


import gin
import hyperion

import trainer


print("one param sweep:")
for config in hyperion.parse_sweep_file("one_param_sweep.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()

print("two param sweep:")
for config in hyperion.parse_sweep_file("two_param_sweep.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()
