#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON:-python3}

"$python_bin" - <<'PY'
import os
import rfc3339_validator

expected = os.environ.get("CANDIDATE_EXPECTED_ROOT")
actual = os.path.realpath(rfc3339_validator.__file__)
if expected and not actual.startswith(os.path.realpath(expected)):
    raise SystemExit("candidate import escaped expected root: %s" % actual)
print("candidate import:", actual)
PY

cd "$repo_root"
"$python_bin" -m pytest -q upstream/tests/test_rfc3339_validator.py
