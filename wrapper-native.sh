#!/bin/bash

set -e

export PYTHONUNBUFFERED=1
export PYTHONPATH=/usr/local/lib/bbs-popcorn

exec python3 -m bbs_popcorn.main "$@"
