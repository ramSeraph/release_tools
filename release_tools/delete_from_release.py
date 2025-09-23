import argparse
import subprocess
import sys
from pathlib import Path

from .utils import command_exists, get_asset_names, get_release_map, run_command

def delete_asset(release, asset_name, repo=None):
    """Delete an asset from a release."""
    print(f"Deleting asset '{asset_name}' from release '{release}'")
    run_command(['gh', 'release', 'delete-asset', release, asset_name, '-y'], repo=repo)

def cli():
    """Main function to delete files from a release."""
    parser = argparse.ArgumentParser(description='Delete files from a GitHub release and its supplementary releases.')
    parser.add_argument('--repo', '-g', help='The GitHub repository in the format 'owner/repo'. If not provided, it will be inferred from the current directory.')
    parser.add_argument('--release', '-r', required=True, help='The base name of the release.')
    parser.add_argument('--file-list', '-f', type=Path, help='Path to a text file with a list of files to delete (one file per line).')
    parser.add_argument('files', nargs='*', help='File names to delete.')
    args = parser.parse_args()

    if not command_exists("gh"):
        print("Error: gh command-line tool is not installed. Please install it to continue.", file=sys.stderr)
        return 1

    if not args.file_list and not args.files:
        parser.error("No files to delete. Please provide a file list with --file-list or specify file names as arguments.")

    files_to_delete = set()
    if args.file_list:
        if args.file_list.exists():
            with open(args.file_list, 'r') as f:
                files_to_delete.update(line.strip() for line in f if line.strip())
        else:
            print(f"Error: File list '{args.file_list}' not found.", file=sys.stderr)
            return 1
            
    if args.files:
        files_to_delete.update(args.files)

    if not files_to_delete:
        print("No files to delete.")
        return 0

    print("Getting release list")
    release_map = get_release_map(args.release, repo=args.repo)
    
    if not release_map:
        print("No releases found to process.", file=sys.stderr)
        return 1
        
    releases_to_process = list(release_map.values())

    print(f"Will process releases: {releases_to_process}")
    print(f"Files to delete: {sorted(list(files_to_delete))}")

    deleted_assets = set()
    for release in releases_to_process:
        print(f"Processing release: {release}")
        assets = get_asset_names(release, repo=args.repo)
        
        assets_set = set(assets)
        assets_to_delete_from_release = files_to_delete.intersection(assets_set)

        if not assets_to_delete_from_release:
            print(f"No matching files to delete in release '{release}'.")
            continue

        for asset in sorted(list(assets_to_delete_from_release)):
            if delete_asset(release, asset, repo=args.repo):
                deleted_assets.add(asset)

    total_count = len(files_to_delete)
    deleted_count = len(deleted_assets)
    skipped_count = total_count - deleted_count

    print("--- Deletion Summary ---")
    print(f"Total files requested for deletion: {total_count}")
    print(f"Successfully deleted files: {deleted_count}")
    print(f"Skipped files (not found in any release): {skipped_count}")
    
    return 0

if __name__ == '__main__':
    sys.exit(cli())
