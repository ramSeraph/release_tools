# Release Tools [![PyPI - Latest Version](https://img.shields.io/pypi/v/gh_release_tools)](https://pypi.org/project/gh_release_tools/) [![GitHub Tag](https://img.shields.io/github/v/tag/ramSeraph/release_tools?filter=v*)](https://github.com/ramSeraph/release_tools/releases/latest)

This project provides a set of tools for managing files in GitHub releases. This assumes that `gh` (the GitHub CLI) is installed and configured on your system, as it is used to interact with GitHub releases.

## Features

- **Generate file lists:** Create a CSV file containing a list of all files in a GitHub release.
- **Upload files to a release:** Upload files from a local directory to a GitHub release, with an option to overwrite existing files.

## Installation

This project is packaged using Hatch. To install the tools, you can run the following command:

```bash
pip install .
```

This will install the `release-tools` package and make the following command-line tools available:

- `generate-lists`
- `upload-to-release`

## Usage

It is recommended to run the tools using `uvx` to avoid dependency conflicts with other installed packages.

### `uvx`

```bash
uvx --from gh_release_tools generate-lists <release_base> <extension>
uvx --from gh_release_tools upload-to-release <tag> <folder> <extension_without_the_leading_dot> [yes_to_overwrite]
```

### `generate-lists`

This tool generates a CSV file named `listing_files.csv` containing a list of assets from a specified GitHub release and its associated `-extra` releases. The CSV file includes the file name, size, and download URL for each asset.

**Usage:**

```bash
generate-lists <release_base> <extension>
```

**Arguments:**

- `<release_base>`: The base name of the GitHub release (e.g., `v1.0.0`).
- `<extension>`: The file extension of the assets to include in the list (e.g., `.zip`).

**Example:**

```bash
generate-lists v1.0.0 .zip
```

This command will generate a `listing_files.csv` file with a list of all `.zip` files from the `v1.0.0` release and any releases named `v1.0.0-extra<number>`.

### `upload-to-release`

This tool uploads files from a local folder to a GitHub release. It can be configured to skip files that already exist in the release or to overwrite them.

**Usage:**

```bash
upload-to-release <tag> <folder> <extension_without_the_leading_dot> [yes_to_overwrite]
```

**Arguments:**

- `<tag>`: The git tag of the release to upload to.
- `<folder>`: The local folder containing the files to upload.
- `<extension_without_the_leading_dot>`: The file extension of the files to upload (e.g., `zip`).
- `[yes_to_overwrite]`: (Optional) Set to `yes` to overwrite existing assets in the release.

**Example:**

```bash
upload-to-release v1.0.0 /path/to/files zip
```

This command will upload all `.zip` files from the `/path/to/files` directory to the `v1.0.0` release. If a file with the same name already exists in the release, it will be skipped. To overwrite existing files, use the following command:

```bash
upload-to-release v1.0.0 /path/to/files zip yes
```

**Note:** These tools are being used for my personal projects and are not meant for general public use.
