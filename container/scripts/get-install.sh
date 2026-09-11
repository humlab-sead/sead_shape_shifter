#!/bin/bash

curl -L https://github.com/humlab-sead/sead_shape_shifter/archive/refs/heads/dev.tar.gz |
  tar -xz \
    --wildcards \
    --strip-components=1 \
    'sead_shape_shifter-dev/container/*'
