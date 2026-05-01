#!/bin/bash

set -e

export PYTHONUNBUFFERED=1
export PYTHONPATH=/app/lib/bbs-popcorn

# --- Inject sponsorblock dans le mpv Flatpak ---
MPV_CONFIG_DIR="$HOME/.var/app/io.mpv.Mpv/config/mpv/scripts"
mkdir -p "$MPV_CONFIG_DIR"

if [ ! -f "$MPV_CONFIG_DIR/sponsorblock.lua" ]; then
    cp /app/share/bbs-popcorn/sponsorblock.lua "$MPV_CONFIG_DIR/sponsorblock.lua"
fi

exec python3 -m bbs_popcorn.main "$@"
