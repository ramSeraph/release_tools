import argparse
import subprocess
import csv
import sys
from pathlib import Path

from .utils import command_exists, get_release_map, run_command

def get_assets(release, ext):
    """Get all assets with a given extension for a given release."""
    output = run_command([
        'gh',
        'release',
        'view',
        release,
        '--json',
        'assets',
        '-q',
        f'.assets[] | select(.name | endswith("{ext}")) | "\\(.name),\\(.size),\\(.url)"'
    ])
    return output.strip()


def cli():
    """Main function to generate file lists and upload to release."""
    parser = argparse.ArgumentParser(description='Generate file lists and upload to a GitHub release.')
    parser.add_argument('--release', '-r', required=True, help='The base name of the release.')
    parser.add_argument('--extension', '-e', action='append', help='File extension to filter assets by.')
    args = parser.parse_args()

    if not command_exists("gh"):
        print("Error: gh command-line tool is not installed. Please install it to continue.", file=sys.stderr)
        return 1

    if not args.extension:
        print("No file extensions provided. Please specify at least one extension using --extension.", file=sys.stderr)
        return 1

    print("Getting file list")
    release_map = get_release_map(args.release)
    releases_to_process = list(release_map.values())
    
    if not releases_to_process:
        print("No releases found to process.", file=sys.stderr)
        return 1

    print(f"Will process releases: {releases_to_process}")

    all_assets = []
    for release in releases_to_process:
        print(f"Processing release: {release}")
        for ext in args.extension:
            assets = get_assets(release, ext)
            if assets:
                # Filter out empty strings that can result from split('\n')
                all_assets.extend([line.strip() for line in assets.split('\n') if line.strip()])

    if not all_assets:
        print("No assets found to process.")
        return 0
        
    csv_file = Path('listing_files.csv')

    with open(csv_file, 'w') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['name', 'size', 'url'])
        for asset_line in all_assets:
            csv_writer.writerow(asset_line.split(',', 2))

    print(f"Uploading {csv_file} to release {args.release}")
    run_command(['gh', 'release', 'upload', args.release, str(csv_file), '--clobber'])

    csv_file.unlink()
            
    return 0

if __name__ == '__main__':
    sys.exit(cli())
