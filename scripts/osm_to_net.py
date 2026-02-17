#!/usr/bin/env python3
"""
Script that converts the filtered OSM files produced by ``scripts/osm_data_fetcher.py``
into SUMO networks via :class:`konexys.modules.environment.road_terrain.map.sumo_manager.SumoManager`.

The input files must live inside ``scripts/osm_data_output`` and are processed in this
order:

1. ``osm_data_softfiltered.osm``
2. ``osm_data_hardfiltered.osm``

The original download is intentionally left untouched. Each run writes its
own output into a dedicated subdirectory under the configured SUMO output
location.
"""

from argparse import ArgumentParser
from pathlib import Path
import logging

from konexys.modules.environment.road_terrain.map.sumo_manager import SumoManager

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = (SCRIPT_DIR / "configs" / "sumo_manager.yaml")
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "playground_data" / "sumo_data_output"
OSM_DATA_DIR = SCRIPT_DIR / "playground_data" / "osm_data_output"

OSM_RUNS = [
    ("osm_data_original.osm", "original"),
    ("osm_data_softfiltered.osm", "softfiltered"),
    ("osm_data_hardfiltered.osm", "hardfiltered"),
]


def _configure_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Convert the original, soft and hard filtered OSM files into SUMO networks."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to sumo_manager.yaml (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Base directory where SUMO outputs are written (default: %(default)s).",
    )
    return parser


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _run_conversion(osm_file: Path, config: Path, output_dir: Path) -> Path:
    manager = SumoManager(config_path=config, output_dir=output_dir)
    return manager.netconvert(map_file_path=osm_file)


def main():
    _setup_logging()
    args = _configure_parser().parse_args()

    if not OSM_DATA_DIR.is_dir():
        logging.error("Expected scripts/osm_data_output directory not found.")
        raise SystemExit(1)

    if not args.config.exists():
        logging.error("SumoManager config cannot be found.")
        raise SystemExit(1)

    logging.info("Starting SUMO conversions")
    logging.info("Input directory: %s", OSM_DATA_DIR)
    logging.info("Config file: %s", args.config)
    logging.info("Base output directory: %s", args.output_dir)

    for file_name, label in OSM_RUNS:
        osm_path = OSM_DATA_DIR / file_name
        if not osm_path.exists():
            logging.warning(
                "Skipping %s because %s is missing.", label, osm_path
            )
            continue

        run_output_dir = args.output_dir / label
        logging.info("Converting %s (%s)", label, osm_path)
        net_path = _run_conversion(osm_path, args.config, run_output_dir)
        logging.info("  %s net file placed at %s", label.capitalize(), net_path)


if __name__ == "__main__":
    main()
