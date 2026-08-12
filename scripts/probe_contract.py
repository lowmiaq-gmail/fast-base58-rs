#!/usr/bin/env python3
import argparse
import importlib.util
import json
from pathlib import Path


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("frozen_base58_oracle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_value(case):
    kind = case["kind"]
    value = case.get("value")
    if kind == "str":
        return value
    if kind == "bytes":
        # value is list of ints
        return bytes(value)
    if kind == "none":
        return None
    if kind == "int":
        return value
    raise ValueError("unknown case kind: %s" % kind)


def observe(func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        if isinstance(result, bytes):
            return {
                "outcome": "return",
                "type": "bytes",
                "value": list(result),
            }
        return {
            "outcome": "return",
            "type": type(result).__name__,
            "value": result,
        }
    except Exception as error:
        return {
            "outcome": "error",
            "type": type(error).__name__,
            "message": str(error),
        }


def observe_const(module, name):
    value = getattr(module, name)
    if isinstance(value, bytes):
        return {"outcome": "return", "type": "bytes", "value": list(value)}
    return {"outcome": "return", "type": type(value).__name__, "value": value}


FUNCTIONS = [
    "b58encode",
    "b58decode",
    "b58encode_check",
    "b58decode_check",
    "b58encode_int",
    "b58decode_int",
    "scrub_input",
    "_get_base58_decode_map",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oracle", type=Path)
    args = parser.parse_args()

    if args.oracle:
        module = load_oracle(args.oracle)
    else:
        import base58 as module

    records = []
    with args.corpus.open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            if case["kind"] == "call":
                func_name = case["function"]
                func = getattr(module, func_name)
                args_list = [decode_value(a) for a in case.get("args", [])]
                kwargs = {}
                for k, v in case.get("kwargs", {}).items():
                    kwargs[k] = decode_value(v)
                records.append(observe(func, *args_list, **kwargs))
            elif case["kind"] == "const":
                records.append(observe_const(module, case["name"]))
    args.output.write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in records) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
