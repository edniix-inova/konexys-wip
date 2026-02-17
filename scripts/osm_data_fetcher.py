#!/usr/bin/env python3
"""
Small script to fetch OSM data using OsmManager.
This script requests a bounding box from the user, queries the OSM server
through the overpass-api, and saves the data in three forms:
- Unfiltered (original)
- Soft-filtered (with elevation data)
- Hard-filtered (strict filtering)
"""

import logging
from pathlib import Path

from konexys.modules.environment.road_terrain.map.osm_manager import OsmManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_bounding_box_from_user():
    """Request bounding box coordinates from the user.
    Returns
    -------
    bounding_box : str
        Bounding box in format "south,west,north,east"
    """
    print("\n" + "="*60)
    print("OSM Data Fetcher")
    print("="*60)
    print("\nPlease enter the bounding box coordinates.")
    print("Format: south,west,north,east (e.g., 48.1,11.5,48.2,11.6)")
    print("\nExamples:")
    print("  Munich area: 48.0,11.4,48.2,11.7")
    print("  Berlin area: 52.4,13.3,52.6,13.5")
    print("-"*60)

    while True:
        bounding_box = input("\nBounding box: ").strip()

        # Validate input
        try:
            coords = list(map(float, bounding_box.split(",")))
            if len(coords) != 4:
                raise ValueError("Expected 4 coordinates")
            south, west, north, east = coords

            # Basic validation
            if not (-90 <= south < north <= 90):
                raise ValueError("Invalid latitude range")
            if not (-180 <= west < east <= 180):
                raise ValueError("Invalid longitude range")

            print(f"\nBounding box validated:")
            print(f"  South: {south}, West: {west}")
            print(f"  North: {north}, East: {east}")
            return bounding_box

        except ValueError as e:
            print(f"\nInvalid input: {e}")
            print("Please enter coordinates in format: south,west,north,east")


def main():
    """Main function to run the OSM data fetcher."""

    # Get current directory (where this script is located)
    script_dir = Path(__file__).parent

    # Configuration file path
    config_path = script_dir / "configs/osm_manager.yaml"

    # Output directory for OSM data
    output_dir = script_dir / "plyaground_data/osm_data_output"

    # Check if config file exists
    if not config_path.exists():
        logging.error(f"Configuration file not found: {config_path}")
        return

    # Get bounding box from user
    bounding_box = get_bounding_box_from_user()

    # Initialize OsmManager
    logging.info("Initializing OsmManager...")
    osm_manager = OsmManager(config_path=config_path, output_dir=output_dir)

    # Download OSM data (unfiltered)
    logging.info("\n" + "="*60)
    logging.info("Step 1: Downloading unfiltered OSM data")
    logging.info("="*60)
    osm_original_path = osm_manager.download(bounding_box=bounding_box)
    logging.info(f"Unfiltered data saved to: {osm_original_path}")

    # Process OSM data (apply filters)
    logging.info("\n" + "="*60)
    logging.info("Step 2: Processing OSM data (applying filters)")
    logging.info("="*60)
    osm_soft_path, osm_hard_path = osm_manager.process(osm_download_path=osm_original_path)

    # Summary
    logging.info("\n" + "="*60)
    logging.info("Processing Complete!")
    logging.info("="*60)
    logging.info(f"Unfiltered OSM data:    {osm_original_path}")
    logging.info(f"Soft-filtered OSM data: {osm_soft_path}")
    logging.info(f"Hard-filtered OSM data: {osm_hard_path}")
    logging.info("\nAll files have been saved successfully.")


if __name__ == "__main__":
    main()