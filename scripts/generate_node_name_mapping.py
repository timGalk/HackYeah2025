#!/usr/bin/env python3
"""Generate mapping from graph node IDs to actual stop/street names.

This script extracts stop_id -> stop_name mappings from GTFS data files
and creates a consolidated mapping file for use with the NetworkX graph.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd


def extract_stop_mapping_from_gtfs(gtfs_zip_path: Path) -> dict[str, str]:
    """Extract stop_id to stop_name mapping from a GTFS zip file.

    Args:
        gtfs_zip_path: Path to the GTFS zip file

    Returns:
        Dictionary mapping stop_id to stop_name
    """
    mapping = {}
    try:
        with zipfile.ZipFile(gtfs_zip_path, "r") as z:
            if "stops.txt" in z.namelist():
                with z.open("stops.txt") as f:
                    df = pd.read_csv(f)
                    if "stop_id" in df.columns and "stop_name" in df.columns:
                        for _, row in df.iterrows():
                            stop_id = str(row["stop_id"])
                            stop_name = str(row["stop_name"])
                            # Keep the first occurrence or combine if different
                            if stop_id not in mapping:
                                mapping[stop_id] = stop_name
    except Exception as e:
        print(f"Warning: Could not process {gtfs_zip_path.name}: {e}")
    return mapping


def main() -> None:
    """Generate node ID to street name mapping from all GTFS sources."""
    # Paths
    project_root = Path(__file__).parent.parent
    otp_data_dir = project_root / "otp_data"
    output_file = project_root / "node_name_mapping.json"

    # Also check if there's a stops.csv in scrapper directory
    scrapper_stops = project_root / "src" / "scrapper" / "stops.csv"

    node_mapping: dict[str, str] = {}

    # Method 1: Read from scrapper/stops.csv if available
    if scrapper_stops.exists():
        print(f"Reading stops from {scrapper_stops}...")
        df = pd.read_csv(scrapper_stops)
        if "stop_id" in df.columns and "stop_name" in df.columns:
            for _, row in df.iterrows():
                stop_id = str(row["stop_id"])
                stop_name = str(row["stop_name"])
                node_mapping[stop_id] = stop_name
            print(f"Loaded {len(node_mapping)} stops from stops.csv")

    # Method 2: Read from GTFS zip files in otp_data
    gtfs_files = list(otp_data_dir.glob("GTFS_*.zip"))
    for gtfs_file in gtfs_files:
        print(f"Processing {gtfs_file.name}...")
        stops_from_zip = extract_stop_mapping_from_gtfs(gtfs_file)
        # Merge, preferring existing entries
        for stop_id, stop_name in stops_from_zip.items():
            if stop_id not in node_mapping:
                node_mapping[stop_id] = stop_name
        print(f"Total stops after processing: {len(node_mapping)}")

    if not node_mapping:
        print("ERROR: No stop data found!")
        return

    # Sort by stop_id for readability
    sorted_mapping = dict(sorted(node_mapping.items()))

    # Save as JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Mapping saved to {output_file}")
    print(f"   Total nodes mapped: {len(sorted_mapping)}")

    # Print some examples
    print("\n📋 Sample mappings:")
    for i, (node_id, name) in enumerate(sorted_mapping.items()):
        if i >= 10:
            break
        print(f"   {node_id} -> {name}")

    # Also create a Python module for easy importing
    py_output = project_root / "src" / "app" / "core" / "node_mapping.py"
    with open(py_output, "w", encoding="utf-8") as f:
        f.write('"""Auto-generated mapping from graph node IDs to stop/street names."""\n\n')
        f.write("from __future__ import annotations\n\n")
        f.write("# Node ID to stop name mapping\n")
        f.write("NODE_NAME_MAPPING: dict[str, str] = ")
        f.write(json.dumps(sorted_mapping, ensure_ascii=False, indent=4))
        f.write("\n\n\n")
        f.write("def get_node_name(node_id: str) -> str | None:\n")
        f.write('    """Get the stop/street name for a given node ID.\n\n')
        f.write("    Args:\n")
        f.write("        node_id: The graph node identifier (stop_id)\n\n")
        f.write("    Returns:\n")
        f.write("        The stop name if found, None otherwise\n")
        f.write('    """\n')
        f.write("    return NODE_NAME_MAPPING.get(node_id)\n")

    print(f"\n✅ Python module saved to {py_output}")


if __name__ == "__main__":
    main()

