#!/usr/bin/env python3
"""
End-to-end OSM → SUMO pipeline.

Steps
-----
1. Ask the user for a bounding box.
2. Download raw OSM data via OsmManager.
3. Apply soft- and hard-filters (OsmManager.process).
4. Convert each OSM file (original, soft-filtered, hard-filtered) to a SUMO
   network via SumoManager.netconvert.
"""

import logging
from argparse import ArgumentParser
from pathlib import Path

from konexys.modules.environment.road_terrain.map.osm_manager import OsmManager
from konexys.modules.environment.road_terrain.map.sumo_manager import SumoManager

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OSM_CONFIG = SCRIPT_DIR / "configs" / "osm_manager.yaml"
DEFAULT_SUMO_CONFIG = SCRIPT_DIR / "configs" / "sumo_manager.yaml"
DEFAULT_OSM_OUTPUT = SCRIPT_DIR / "playground_data" / "osm_data_output"
DEFAULT_SUMO_OUTPUT = SCRIPT_DIR / "playground_data" / "sumo_data_outout"


def _configure_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Download OSM data, filter it, and convert it to SUMO networks."
    )
    parser.add_argument(
        "--osm-config",
        type=Path,
        default=DEFAULT_OSM_CONFIG,
        help="Path to osm_manager.yaml (default: %(default)s).",
    )
    parser.add_argument(
        "--sumo-config",
        type=Path,
        default=DEFAULT_SUMO_CONFIG,
        help="Path to sumo_manager.yaml (default: %(default)s).",
    )
    parser.add_argument(
        "--osm-output",
        type=Path,
        default=DEFAULT_OSM_OUTPUT,
        help="Directory where OSM files are written (default: %(default)s).",
    )
    parser.add_argument(
        "--sumo-output",
        type=Path,
        default=DEFAULT_SUMO_OUTPUT,
        help="Base directory where SUMO networks are written (default: %(default)s).",
    )
    return parser


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _get_bounding_box() -> str:
    """Prompt the user for a bounding box and return it as a validated string."""
    print("\n" + "=" * 60)
    print("OSM → SUMO Pipeline")
    print("=" * 60)
    print("\nPlease enter the bounding box coordinates.")
    print("Format: south,west,north,east  (e.g. 48.1,11.5,48.2,11.6)")
    print("\nExamples:")
    print("  Munich area: 48.0,11.4,48.2,11.7")
    print("  Berlin area: 52.4,13.3,52.6,13.5")
    print("-" * 60)

    while True:
        bounding_box = input("\nBounding box: ").strip()
        try:
            coords = list(map(float, bounding_box.split(",")))
            if len(coords) != 4:
                raise ValueError("Expected 4 coordinates")
            south, west, north, east = coords
            if not (-90 <= south < north <= 90):
                raise ValueError("Invalid latitude range")
            if not (-180 <= west < east <= 180):
                raise ValueError("Invalid longitude range")
            print(f"\nBounding box validated:")
            print(f"  South: {south}, West: {west}")
            print(f"  North: {north}, East: {east}")
            return bounding_box
        except ValueError as exc:
            print(f"\nInvalid input: {exc}")
            print("Please enter coordinates in format: south,west,north,east")


def _download_and_filter(bounding_box: str, osm_config: Path, osm_output: Path):
    """Download OSM data and apply soft/hard filters. Returns all three file paths."""
    logging.info("=" * 60)
    logging.info("Step 1: Downloading OSM data")
    logging.info("=" * 60)
    osm_manager = OsmManager(config_path=osm_config, output_dir=osm_output)
    original_path = osm_manager.download(bounding_box=bounding_box)
    logging.info("Unfiltered data saved to: %s", original_path)

    logging.info("=" * 60)
    logging.info("Step 2: Applying filters")
    logging.info("=" * 60)
    soft_path, hard_path = osm_manager.process(osm_download_path=original_path)
    logging.info("Soft-filtered data saved to: %s", soft_path)
    logging.info("Hard-filtered data saved to: %s", hard_path)

    return original_path, soft_path, hard_path


def _convert_to_sumo(osm_path: Path, label: str, sumo_config: Path, sumo_output: Path):
    """Convert a single OSM file to a SUMO network."""
    run_output_dir = sumo_output / label
    manager = SumoManager(config_path=sumo_config, output_dir=run_output_dir)
    net_path = manager.netconvert(map_file_path=osm_path)
    logging.info("  %s net file placed at %s", label.capitalize(), net_path)
    return net_path


def main():
    _setup_logging()
    args = _configure_parser().parse_args()

    for name, path in [("OSM config", args.osm_config), ("SUMO config", args.sumo_config)]:
        if not path.exists():
            logging.error("%s not found: %s", name, path)
            raise SystemExit(1)

    bounding_box = _get_bounding_box()

    original_path, soft_path, hard_path = _download_and_filter(
        bounding_box, args.osm_config, args.osm_output
    )

    logging.info("=" * 60)
    logging.info("Step 3: Converting OSM files to SUMO networks")
    logging.info("=" * 60)

    conversions = [
        (original_path, "original"),
        (soft_path, "softfiltered"),
        (hard_path, "hardfiltered"),
    ]

    results = {}
    for osm_path, label in conversions:
        if not osm_path.exists():
            logging.warning("Skipping %s — file not found: %s", label, osm_path)
            continue
        logging.info("Converting %s (%s)", label, osm_path)
        results[label] = _convert_to_sumo(osm_path, label, args.sumo_config, args.sumo_output)

    logging.info("=" * 60)
    logging.info("Pipeline complete!")
    logging.info("=" * 60)
    logging.info("OSM files:")
    logging.info("  Original:      %s", original_path)
    logging.info("  Soft-filtered: %s", soft_path)
    logging.info("  Hard-filtered: %s", hard_path)
    logging.info("SUMO networks:")
    for label, net_path in results.items():
        logging.info("  %-14s %s", label + ":", net_path)


if __name__ == "__main__":
    main()
