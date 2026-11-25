#!/bin/bash
# Independent engine audit (hand-computed tests). Run from anywhere.
cd "$(dirname "$0")" && for f in t0*.py; do python3 "$f" || echo "ERROR in $f"; done
