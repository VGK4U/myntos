#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/MyntReal_Latest" && pwd)"
cd "$DIR"
bash "$DIR/start_background.sh"
open "http://localhost:5001/hub"
