#!/bin/bash
cd /home/user/audit/engine && for f in t0*.py; do python3 "$f" || echo "ERROR in $f"; done
