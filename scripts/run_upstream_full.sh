#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}

# Verify candidate import is not the upstream frozen module
"$python_bin" - <<'PY'
import os
import base58

expected = os.environ.get("CANDIDATE_EXPECTED_ROOT")
actual = os.path.realpath(base58.__file__)
if expected and not actual.startswith(os.path.realpath(expected)):
    raise SystemExit("candidate import escaped expected root: %s" % actual)
print("candidate import:", actual)
PY

cd "$repo_root"
"$python_bin" -m pytest -q upstream/test_base58.py upstream/test_base45.py
