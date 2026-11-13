"""Compare independently integrity-checked reports across numerical platforms.

Original comparison code: MIT. Input data and derived reports retain their
separate source licences. Run each report through atlas-quant verify first.
"""
import argparse
import json
import math
from pathlib import Path


def compare_reports(left, right):
    result = {"float_values_compared": 0, "different_float_values": 0,
              "maximum_absolute_difference": 0.0,
              "maximum_scaled_difference": 0.0}
    # These exact content hashes necessarily change when float encodings differ.
    # Each complete report must separately pass the engine's integrity verifier.
    hash_paths = {".integrity_sha256", ".council.report_sha256"}

    def walk(a, b, path=""):
        if path in hash_paths:
            return
        if type(a) is not type(b):
            raise ValueError("Type mismatch: " + path)
        if isinstance(a, dict):
            if set(a) != set(b):
                raise ValueError("Key mismatch: " + path)
            for key in a:
                walk(a[key], b[key], path + "." + key)
        elif isinstance(a, list):
            if len(a) != len(b):
                raise ValueError("Length mismatch: " + path)
            for index, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + f"[{index}]")
        elif isinstance(a, float):
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("Non-finite value: " + path)
            result["float_values_compared"] += 1
            result["different_float_values"] += int(a != b)
            difference = abs(a - b)
            result["maximum_absolute_difference"] = max(result["maximum_absolute_difference"], difference)
            result["maximum_scaled_difference"] = max(result["maximum_scaled_difference"], difference / max(1, abs(a), abs(b)))
            if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("Numerical mismatch: " + path)
        elif a != b:
            raise ValueError("Discrete mismatch: " + path)

    walk(left, right)
    return {"status": "passed_with_floating_point_tolerance",
            "relative_tolerance": 1e-10, "absolute_tolerance": 1e-10,
            "ignored_content_hash_paths": sorted(hash_paths),
            "other_non_float_values": "exact_match", **result,
            "left_integrity_sha256": left.get("integrity_sha256"),
            "right_integrity_sha256": right.get("integrity_sha256"),
            "meaning": "Numerical reproduction, not prospective performance or bitwise identity."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare_reports(json.loads(args.left.read_text()),
                                     json.loads(args.right.read_text())), indent=2))
