#!/usr/bin/env python


import gin
import hyperion

import trainer


print("union of products:")
for config in hyperion.parse_sweep_file("union_of_products.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()

print("implicit product:")
for config in hyperion.parse_sweep_file("implicit_product.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
print()

print("explicit product:")
for config in hyperion.parse_sweep_file("explicit_product.hyp"):
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
