#!/usr/bin/env python


import gin
import hyperion

import trainer


for config in hyperion.parse_sweep_file("sweep.hyp"):
    gin.parse_config(config)
    trainer.train()
    print()
