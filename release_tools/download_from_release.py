import argparse
import sys
from pathlib import Path

from .utils import command_exists, get_asset_names, get_release_map, run_command


def download_assets(release, assets, output_dir=None, repo=None):
    """Download a list of assets from a release."""
    print(f"Downloading {len(assets)} asset(s) from release '{release}'")
    command = ['gh', 'release', 'download', release]
    for asset in assets:
        command.extend(['-p', asset])
    if output_dir:
        command.extend(['--dir', str(output_dir)])
    run_command(command, repo=repo)


def main(argv):
    """Main function to download files from a release."""
    parser = argparse.ArgumentParser(description='Download files from a GitHub release and its supplementary releases.')
    parser.add_argument('--repo', '-g', help='The GitHub repository in the format \'owner/repo\'. If not provided, it will be inferred from the current directory.')
    parser.add_argument('--release', '-r', required=True, help='The base name of the release.')
    parser.add_argument('--file-list', '-f', type=Path, help='Path to a text file with a list of files to download (one file per line).')
    parser.add_argument('--output-dir', '-d', type=Path, help='The directory to save the downloaded files. If not provided, files are downloaded to the current directory.')
    parser.add_argument('--skip-existing', action='store_true', help='Skip downloading files that already exist in the output directory.')
    parser.add_argument('--batch-size', '-b', type=int, default=1, help='The number of files to download in a single batch. (default: 50)')
    parser.add_argument('files', nargs='*', help='File names to download.')
    args = parser.parse_args(argv)

    if not command_exists("gh"):
        print("Error: gh command-line tool is not installed. Please install it to continue.", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.file_list and not args.files:
        parser.error("No files to download. Please provide a file list with --file-list or specify file names as arguments.")

    files_to_download = set()
    if args.file_list:
        if args.file_list.exists():
            with open(args.file_list, 'r') as f:
                files_to_download.update(line.strip() for line in f if line.strip())
        else:
            print(f"Error: File list '{args.file_list}' not found.", file=sys.stderr)
            return 1
            
    if args.files:
        files_to_download.update(args.files)

    if not files_to_download:
        print("No files to download.")
        return 0

    print("Getting release list")
    release_map = get_release_map(args.release, repo=args.repo)
    
    if not release_map:
        print("No releases found to process.", file=sys.stderr)
        return 1
        
    releases_to_process = list(release_map.values())

    print(f"Will process releases: {releases_to_process}")
    print(f"Files to download: {sorted(list(files_to_download))}")

    asset_to_release_map = {}
    release_to_assets_map = {}
    for release in releases_to_process:
        print(f"Fetching assets from release: {release}")
        assets = get_asset_names(release, repo=args.repo)
        for asset in assets:
            if asset in files_to_download:
                asset_to_release_map[asset] = release
                release_to_assets_map.setdefault(release, []).append(asset)

    output_dir = args.output_dir or Path('.')

    downloaded_assets = set()
    skipped_assets = set()
    failed_assets = set()

    for asset in asset_to_release_map.keys():
        output_file = output_dir / asset
        if args.skip_existing and output_file.exists():
            skipped_assets.add(asset)

    skipped_count = len(skipped_assets)
    if skipped_count > 0:
        print(f"Skipping {skipped_count} files that already exist: {', '.join(list(skipped_assets)[:5])}{'...' if skipped_count > 5 else ''}")


    found_assets = set(asset_to_release_map.keys())
    not_found_assets = files_to_download - found_assets
    
    for asset in sorted(list(not_found_assets)):
        print(f"Asset '{asset}' not found in any of the releases.", file=sys.stderr)

    to_download_count = len(files_to_download) - len(skipped_assets) - len(not_found_assets)

    for release, assets in release_to_assets_map.items():
        assets_to_download_for_release = []
        for asset in sorted(assets):
            if asset not in skipped_assets:
                assets_to_download_for_release.append(asset)

        if not assets_to_download_for_release:
            continue

        batch_size = args.batch_size
        for i in range(0, len(assets_to_download_for_release), batch_size):
            batch = assets_to_download_for_release[i:i+batch_size]
            try:
                download_assets(release, batch, args.output_dir, repo=args.repo)
                downloaded_assets.update(batch)
                print(f"Downloaded {len(downloaded_assets)} of {to_download_count} files...")
            except Exception as e:
                print(f"Failed to download a batch of {len(batch)} files from {release}: {e}", file=sys.stderr)
                for asset in batch:
                    output_file = output_dir / asset
                    if not output_file.exists():
                        failed_assets.add(asset)

    total_count = len(files_to_download)
    downloaded_count = len(downloaded_assets)
    skipped_count = len(skipped_assets)
    not_found_count = len(not_found_assets)
    failed_count = len(failed_assets)

    print("--- Download Summary ---")
    print(f"Total files requested for download: {total_count}")
    print(f"Successfully downloaded files: {downloaded_count}")
    print(f"Skipped existing files: {skipped_count}")
    print(f"Files not found: {not_found_count}")
    print(f"Files failed to download: {failed_count}")
    
    if failed_count > 0:
        return 1
    
    return 0

def cli():
    return main(sys.argv[1:])
