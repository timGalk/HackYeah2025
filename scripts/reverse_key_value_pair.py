#!/usr/bin/env python3
import json
import argparse
from typing import Any, Dict


def reverse_keys_values(data: Dict[str, Any], safe: bool = True) -> Dict[str, Any]:
    """
    Reverse keys and values in a JSON-compatible dictionary.

    Args:
        data (dict): Input dictionary.
        safe (bool): If True, converts non-hashable values to strings.

    Returns:
        dict: Dictionary with keys and values swapped.
    """
    reversed_dict = {}
    for key, value in data.items():
        try:
            new_key = value if isinstance(value, (str, int, float, bool)) else str(value)
            reversed_dict[new_key] = key
        except TypeError:
            if safe:
                reversed_dict[str(value)] = key
            else:
                raise
    return reversed_dict


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reverse keys and values in a JSON file."
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Path to the input JSON file."
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Path to save the output JSON file."
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Disable safe mode (will raise errors for unhashable types).",
    )

    args = parser.parse_args()

    # Read input JSON
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    if not isinstance(data, dict):
        print("Error: Input JSON must be a top-level object (dictionary).")
        return

    # Reverse and write output
    reversed_data = reverse_keys_values(data, safe=not args.unsafe)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(reversed_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Reversed JSON saved to {args.output}")
    except Exception as e:
        print(f"Error writing output file: {e}")


if __name__ == "__main__":
    main()
