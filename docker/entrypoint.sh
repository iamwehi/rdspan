#!/bin/sh
set -eu
cd /app
python -m rdspan seed
if python -m rdspan generate-audio; then
  :
else
  echo "rdspan: Piper audio generation failed; typed drills still work. Retry with: python -m rdspan generate-audio" >&2
fi
exec python -m rdspan serve
