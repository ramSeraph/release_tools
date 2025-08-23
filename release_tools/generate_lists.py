import argparse
import subprocess
import os
import csv
from pathlib import Path

from .utils import get_release_map

def get_assets(release, ext):
    """Get assets for a given release and filter by extension."""
    try:
        result = subprocess.run(
            [
                'gh', 'release', 'view', release, '--json', 'assets',
                '-q', f".assets[] | select(.name | endswith(\"{ext}\")) | \"\(.name),\(.size),\(.url)\""
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting assets for release {release}: {e}")
        return None

def cli():
    """Main function to generate file lists and upload to release."""
    parser = argparse.ArgumentParser(description='Generate file lists and upload to a GitHub release.')
    parser.add_argument('--release', '-r', required=True, help='The base name of the release.')
    parser.add_argument('--extension', '-e', action='append', help='File extension to filter assets by.')
    args = parser.parse_args()

    if not args.extension:
        print("No file extensions provided. Please specify at least one extension using --extension.")
        return


    print("Getting file list")
    release_map = get_release_map(args.release)
    releases_to_process = list(release_map.values())
    
    if not releases_to_process:
        print("No releases found to process.")
        return

    print(f"Will process releases: {releases_to_process}")

    all_assets = []
    for release in releases_to_process:
        print(f"Processing release: {release}")
        for ext in args.extension:
            assets = get_assets(release, ext)
            if assets:
                # Filter out empty strings that can result from split('\n')
                all_assets.extend([line for line in assets.split('\n') if line])

    if not all_assets:
        print("No assets found to process.")
        return
        
    csv_file = Path('listing_files.csv')
    with open(csv_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['name', 'size', 'url'])
        for asset_line in all_assets:
            csv_writer.writerow(asset_line.split(',', 2))

    print(f"Uploading {csv_file} to release {args.release}")
    try:
        subprocess.run(
            ['gh', 'release', 'upload', args.release, str(csv_file), '--clobber'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error uploading file to release: {e}")
    finally:
        csv_file.unlink()

if __name__ == '__main__':
    cli()
