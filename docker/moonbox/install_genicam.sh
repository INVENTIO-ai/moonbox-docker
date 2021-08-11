#!/usr/bin/env bash

. /opt/conda/bin/activate

set -euo pipefail

echo Install GeniCam

pip install genicam harvesters==1.3.1
