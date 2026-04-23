#!/bin/sh
set -eu

export PYTHONUNBUFFERED=1
export PYTHONPATH=/app/lib/bbs-popcorn

exec python3 -m bbs_popcorn.main
