#!/bin/sh
set -eu
cd /app
python -m rdspan seed
exec python -m rdspan serve
