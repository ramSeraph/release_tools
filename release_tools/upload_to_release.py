import argparse
import subprocess
import sys
from pathlib import Path

from .utils import get_release_map

def command_exists(cmd):
    return subprocess.run(f"command -v {cmd}", shell=True, capture_output=True, text=True).returncode == 0

FIRST_RELEASE_MAX_ASSETS = 988
OTHER_RELEASE_MAX_ASSETS = 998

class ReleaseMapper:
    def __init__(self, main_tag):
        self.release_to_assets = {}
        self.main_tag = main_tag
        self.assets_to_releases = {}

    def add_release(self, release):
        if release not in self.release_to_assets:
            self.release_to_assets[release] = set()

    def add_asset(self, asset, release):
        if release not in self.release_to_assets:
            self.release_to_assets[release] = set()

        self.release_to_assets[release].add(asset)

        self.assets_to_releases[asset] = release

    def get_available_releases(self):
        available_releases = []

        for release, assets in self.release_to_assets.items():
            max_assets = FIRST_RELEASE_MAX_ASSETS if release == self.main_tag else OTHER_RELEASE_MAX_ASSETS

            count = len(assets)
            if count < max_assets:
                available_releases.append(release)

        return available_releases

    def get_release_for_asset(self, asset):
        if asset in self.assets_to_releases:
            return self.assets_to_releases[asset]
        return None

def get_next_num(release_map):
    nums = sorted(release_map.keys())

    for n in nums:
        if n + 1 not in nums:
            return n + 1

    return nums[-1] + 1

def get_repo_name():
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting repository name: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def get_release_title(tag):
    try:
        result = subprocess.run(
            ["gh", "release", "view", tag, "--json", "name", "-q", ".name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting release title for tag {tag}: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def create_release(next_num, main_tag):

    new_release = f"{main_tag}-extra{next_num}"
    print(f"Creating new release '{new_release}'...")
    repo_name = get_repo_name()
    main_release_title = get_release_title(main_tag)
    main_release_url = f"https://github.com/{repo_name}/releases/tag/{main_tag}"

    new_release_title = f"{main_release_title} Supplementary{next_num})"
    listing_files_url = f"https://github.com/{repo_name}/releases/download/{main_tag}/listing_files.csv"

    try:
        subprocess.run(
            ["gh", "release", "create", new_release, "--target", "main", "--title", new_release_title, "--notes", f"Extension of [{main_tag}]({main_release_url})\n\n List of files and their sizes is at [listing_files.csv]({listing_files_url})"],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Created release: {new_release}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating release: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    return new_release

def get_existing_assets(release):
    print(f"Fetching assets from release: {release}")

    assets = []
    try:
        result = subprocess.run(
            ["gh", "release", "view", release, "--json", "assets", "-q", ".assets[].name"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for asset_name in result.stdout.strip().split('\n'):
                if asset_name:
                    assets.append(asset_name)
    except subprocess.CalledProcessError:
        # This can happen if a release has no assets
        pass

    return assets



def cli():
    parser = argparse.ArgumentParser(
        description="Upload files to a GitHub release, skipping existing files.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--release", '-r', help="The git tag of the release to upload to.")
    parser.add_argument("--folder", '-d', help="The local folder containing the files to upload.", type=Path)
    parser.add_argument("--extension", '-e', action='append', help="The extension of the files to upload.")
    parser.add_argument("--create-extra-releases", "-x", action="store_true", help="Create extra releases if needed.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing assets.",
    )
    args = parser.parse_args()

    if not command_exists("gh"):
        print("Error: gh command-line tool is not installed. Please install it to continue.", file=sys.stderr)
        sys.exit(1)

    if not args.folder.is_dir():
        print(f"Error: Folder '{args.folder}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching existing assets for releases matching pattern '{args.release}(-extra[0-9]+)?'...")

    release_map = get_release_map(args.release)
    releases_to_process = list(release_map.values())

    if not releases_to_process:
        print(f"Error: No releases found matching pattern '{args.tag}(-extra[0-9]+)?'.", file=sys.stderr)
        sys.exit(1)

    if args.release not in releases_to_process:
        print(f"Error: Specified main release '{args.release}' not found among fetched releases.", file=sys.stderr)
        sys.exit(1)

    print(f"Found releases: {', '.join(releases_to_process)}")

    release_mapper = ReleaseMapper(args.release)

    for rel in releases_to_process:
        release_mapper.add_release(args.release)
        assets = get_existing_assets(rel)
        for asset in assets:
            release_mapper.add_asset(asset, rel)

    print(f"Starting upload process from folder '{args.folder}'...")

    files_to_upload = []
    for ext in args.extension or []:
        files_to_upload += sorted(list(args.folder.glob(f"*{args.extension}")))

    for file_path in files_to_upload:
        available_releases = release_mapper.get_available_releases()

        filename = file_path.name

        print(f"Processing file: {filename}")

        release = release_mapper.get_release_for_asset(filename)

        if release:
            if args.overwrite:
                print(f"  -> Overwriting '{filename}' in release '{release}'...")
                upload_asset(release, file_path, clobber=True)
            else:
                print(f"  -> Skipping '{filename}', it already exists in release '{release}'.")

            continue

        if len(available_releases) == 0:
            if not args.create_extra_releases:
                print(f"Error: All existing releases are full. No space to upload '{filename}'.", file=sys.stderr)
                sys.exit(1)
            else:
                next_num = get_next_num(release_map)
                new_release = create_release(next_num, args.release)
                release_mapper.add_release(new_release)
                available_releases.append(new_release)

        upload_target = available_releases[0]
        print(f"  -> Uploading '{filename}' to '{upload_target}'...")
        upload_asset(upload_target, file_path)
        release_mapper.add_asset(filename, upload_target)

    print("Upload process complete.")



def upload_asset(release, file_path, clobber=False):
    command = ["gh", "release", "upload", release, str(file_path)]
    if clobber:
        command.append("--clobber")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error uploading asset: {e.stderr}", file=sys.stderr)


if __name__ == "__main__":
    cli()
