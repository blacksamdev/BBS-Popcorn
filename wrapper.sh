#!/bin/bash

set -e

# Lance Python dans l’environnement Flatpak
exec python3 /app/bin/main.py "$@"
