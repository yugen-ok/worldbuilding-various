#!/usr/bin/env python3
"""Validate that all file paths are correctly configured"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

def validate_paths():
    """Validate all file paths in the configuration"""
    errors = []
    warnings = []

    print("="*60)
    print("PATH VALIDATION")
    print("="*60)

    # Check JSON configs
    configs = ["configs/adaptive_config.json", "configs/naive_config.json"]
    for config_file in configs:
        config_path = Path(config_file)
        print(f"\n[1] Checking {config_file}...")

        if not config_path.exists():
            errors.append(f"  [X] Config file not found: {config_file}")
            continue
        print(f"  [OK] Config file exists")

        # Load and check SUMO config reference
        with open(config_path) as f:
            config_data = json.load(f)

        sumo_cfg = config_data.get("simulation", {}).get("sumo_config")
        if not sumo_cfg:
            errors.append(f"  [X] No sumo_config specified in {config_file}")
            continue

        sumo_cfg_path = Path(sumo_cfg)
        print(f"  -> References: {sumo_cfg}")

        if not sumo_cfg_path.exists():
            errors.append(f"  [X] SUMO config not found: {sumo_cfg}")
            continue
        print(f"  [OK] SUMO config exists")

        # Parse SUMO config and check XML file references
        print(f"\n[2] Checking {sumo_cfg}...")
        tree = ET.parse(sumo_cfg_path)
        root = tree.getroot()

        # Check network file
        net_file = root.find(".//net-file")
        if net_file is not None:
            net_path_str = net_file.get("value")
            # Resolve relative to the SUMO config file location
            net_path = (sumo_cfg_path.parent / net_path_str).resolve()
            print(f"  -> Network file: {net_path_str}")

            if not net_path.exists():
                errors.append(f"  [X] Network file not found: {net_path}")
            else:
                print(f"  [OK] Network file exists: {net_path}")

        # Check route files
        route_files = root.find(".//route-files")
        if route_files is not None:
            route_path_str = route_files.get("value")
            # Resolve relative to the SUMO config file location
            route_path = (sumo_cfg_path.parent / route_path_str).resolve()
            print(f"  -> Route file: {route_path_str}")

            if not route_path.exists():
                errors.append(f"  [X] Route file not found: {route_path}")
            else:
                print(f"  [OK] Route file exists: {route_path}")

    # Check network directory
    print(f"\n[3] Checking network directory...")
    network_dir = Path("network")
    if not network_dir.exists():
        errors.append("  [X] network/ directory not found")
    else:
        print(f"  [OK] network/ directory exists")
        xml_files = ["network.nod.xml", "network.edg.xml", "network.net.xml", "routes.rou.xml"]
        for xml_file in xml_files:
            xml_path = network_dir / xml_file
            if not xml_path.exists():
                errors.append(f"  [X] Missing: {xml_path}")
            else:
                print(f"  [OK] {xml_file}")

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    if errors:
        print("\n[ERROR] ERRORS FOUND:")
        for error in errors:
            print(error)

    if warnings:
        print("\n[WARN] WARNINGS:")
        for warning in warnings:
            print(warning)

    if not errors and not warnings:
        print("\n[SUCCESS] All paths are correctly configured!")
        print("\nThe simulation should work correctly.")
        return True
    elif not errors:
        print("\n[SUCCESS] No critical errors, but check warnings above.")
        return True
    else:
        print("\n[FAIL] Please fix the errors above before running the simulation.")
        return False

if __name__ == "__main__":
    success = validate_paths()
    exit(0 if success else 1)
