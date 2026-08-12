#!/usr/bin/env python3
import argparse
import importlib.util
import json
from pathlib import Path


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("frozen_rfc3339_oracle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode(case):
    kind = case["kind"]
    value = case.get("value")
    if kind == "str":
        return value
    if kind == "bytes":
        return value.encode("ascii")
    if kind == "none":
        return None
    if kind == "int":
        return value
    raise ValueError("unknown case kind: %s" % kind)


def observe(function, value):
    try:
        result = function(value)
    except Exception as error:  # contract probe intentionally captures errors
        return {
            "outcome": "error",
            "type": type(error).__name__,
            "message": str(error),
        }
    return {
        "outcome": "return",
        "type": type(result).__name__,
        "value": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oracle", type=Path)
    args = parser.parse_args()

    if args.oracle:
        module = load_oracle(args.oracle)
    else:
        import rfc3339_validator as module

    records = []
    with args.corpus.open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            records.append(observe(module.validate_rfc3339, decode(case)))
    args.output.write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in records) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
