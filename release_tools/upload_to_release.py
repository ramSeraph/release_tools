import argparse
import sys
from pathlib import Path

from .utils import command_exists, get_release_map, get_asset_names, get_repo_name_from_gh, run_command

class CliError(Exception):
    pass

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



def get_release_title(tag, repo=None):
    try:
        cmd = ["gh", "release", "view", tag, "--json", "name", "-q", ".name"]
        result = run_command(cmd, repo=repo)
        return result.strip()
    except Exception as e:
        raise CliError(f"Error getting release title for tag {tag}: {e}")

def create_release(next_num, main_tag, repo=None):
    new_release = f"{main_tag}-extra{next_num}"
    print(f"Creating new release '{new_release}'...")
    repo_name = get_repo_name_from_gh(repo)
    main_release_title = get_release_title(main_tag, repo=repo)
    main_release_url = f"https://github.com/{repo_name}/releases/tag/{main_tag}"

    new_release_title = f"{main_release_title} Supplementary{next_num}"
    listing_files_url = f"https://github.com/{repo_name}/releases/download/{main_tag}/listing_files.csv"

    try:
        cmd = ["gh", "release", "create", new_release, "--target", "main", "--title", new_release_title, "--notes", f"Extension of [{main_tag}]({main_release_url})\n\n List of files and their sizes is at [listing_files.csv]({listing_files_url})"]
        run_command(cmd, repo=repo)
        print(f"Created release: {new_release}")
    except Exception as e:
        raise CliError(f"Error creating release: {e}")

    return new_release

def upload_assets(release, file_paths, clobber=False, repo=None):
    """Upload a list of assets to a release."""
    command = ["gh", "release", "upload", release]
    command.extend([str(p) for p in file_paths])

    if clobber:
        command.append("--clobber")
    try:
        print(f"Uploading {len(file_paths)} asset(s) to release '{release}'...")
        run_command(command, repo=repo)
        print(f"Successfully uploaded {len(file_paths)} assets.")
    except Exception as e:
        print(f"Error uploading batch of {len(file_paths)} assets: {e}", file=sys.stderr)
        raise


def cli():
    try:
        parser = argparse.ArgumentParser(
            description="Upload files to a GitHub release, skipping existing files.",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        parser.add_argument('--repo', '-g', help='The GitHub repository in the format \'owner/repo\'. If not provided, it will be inferred from the current directory.')
        parser.add_argument("--release", '-r', help="The git tag of the release to upload to.")
        parser.add_argument("--folder", '-d', help="The local folder containing the files to upload.", type=Path)
        parser.add_argument("--extension", '-e', action='append', help="The extension of the files to upload.")
        parser.add_argument("--create-extra-releases", "-x", action="store_true", help="Create extra releases if needed.")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Allow overwriting existing assets.",
        )
        parser.add_argument('--batch-size', '-b', type=int, default=1, help='The number of files to upload in a single batch. (default: 50)')
        args = parser.parse_args()

        if not command_exists("gh"):
            raise CliError("Error: gh command-line tool is not installed. Please install it to continue.")

        if not args.folder.is_dir():
            raise CliError(f"Error: Folder '{args.folder}' not found.")

        print(f"Fetching existing assets for releases matching pattern '{args.release}(-extra[0-9]+)?'...")

        release_map = get_release_map(args.release, repo=args.repo)
        releases_to_process = list(release_map.values())

        if not releases_to_process:
            raise CliError(f"Error: No releases found matching pattern '{args.release}(-extra[0-9]+)?'.")

        if args.release not in releases_to_process:
            raise CliError(f"Error: Specified main release '{args.release}' not found among fetched releases.")

        print(f"Found releases: {', '.join(releases_to_process)}")

        release_mapper = ReleaseMapper(args.release)

        for rel in releases_to_process:
            release_mapper.add_release(rel)
            print(f"Fetching assets from release: {rel}")
            assets = get_asset_names(rel, repo=args.repo)
            for asset in assets:
                release_mapper.add_asset(asset, rel)

        print(f"Starting upload process from folder '{args.folder}'...")

        files_to_upload_paths = []
        for ext in args.extension or []:
            files_to_upload_paths += sorted(list(args.folder.glob(f"*{ext}")))

        total_files = len(files_to_upload_paths)
        
        files_to_skip = []
        files_to_overwrite = {}  # release -> list of file_paths
        files_for_new_upload = []

        for file_path in files_to_upload_paths:
            filename = file_path.name
            release = release_mapper.get_release_for_asset(filename)

            if release:
                if args.overwrite:
                    files_to_overwrite.setdefault(release, []).append(file_path)
                else:
                    files_to_skip.append(file_path)
            else:
                files_for_new_upload.append(file_path)
        
        skipped_count = len(files_to_skip)
        upload_count_target = total_files - skipped_count
        if skipped_count > 0:
            skipped_filenames = [f.name for f in files_to_skip]
            print(f"Skipping {skipped_count} files that already exist: {', '.join(skipped_filenames[:5])}{'...' if skipped_count > 5 else ''}")

        overwritten_assets = set()
        failed_uploads = set()
        newly_uploaded_assets = set()

        for release, file_paths in files_to_overwrite.items():
            print(f"Overwriting {len(file_paths)} files in release '{release}'...")
            batch_size = args.batch_size
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                try:
                    upload_assets(release, batch, clobber=True, repo=args.repo)
                    overwritten_assets.update(p.name for p in batch)
                    uploaded_count = len(overwritten_assets) + len(newly_uploaded_assets)
                    print(f"Uploaded {uploaded_count} of {upload_count_target} files...")
                except Exception:
                    failed_uploads.update(p.name for p in batch)
        
        uploads_by_release = {}
        
        print(f"Processing {len(files_for_new_upload)} new files to upload...")
        for i, file_path in enumerate(files_for_new_upload, 1):
            filename = file_path.name
            print(f"[{i}/{len(files_for_new_upload)}] Assigning release for: {filename}")
            available_releases = release_mapper.get_available_releases()

            if not available_releases:
                if args.create_extra_releases:
                    next_num = get_next_num(release_map)
                    new_release = create_release(next_num, args.release, repo=args.repo)
                    release_mapper.add_release(new_release)
                    available_releases.append(new_release)
                    release_map[next_num] = new_release
                else:
                    print(f"Error: All existing releases are full. No space to upload '{filename}'. Skipping.", file=sys.stderr)
                    failed_uploads.add(filename)
                    continue

            upload_target = available_releases[0]
            uploads_by_release.setdefault(upload_target, []).append(file_path)
            release_mapper.add_asset(filename, upload_target)

        for release, file_paths in uploads_by_release.items():
            batch_size = args.batch_size
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                try:
                    upload_assets(release, batch, repo=args.repo)
                    newly_uploaded_assets.update(p.name for p in batch)
                    uploaded_count = len(overwritten_assets) + len(newly_uploaded_assets)
                    print(f"Uploaded {uploaded_count} of {upload_count_target} files...")
                except Exception:
                    failed_uploads.update(p.name for p in batch)


        print("Upload process complete.")
        print()
        print("--- Summary ---")
        print(f"Total files processed: {total_files}")
        print(f"Files newly uploaded:  {len(newly_uploaded_assets)}")
        print(f"Files skipped:         {skipped_count}")
        print(f"Files overwritten:     {len(overwritten_assets)}")
        print(f"Files failed to upload(possibly overestimated): {len(failed_uploads)}")

        if len(failed_uploads) > 0:
            print("Failed files:", ", ".join(sorted(list(failed_uploads))))
            return 1

        return 0
    except CliError as e:
        print(e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(cli())
