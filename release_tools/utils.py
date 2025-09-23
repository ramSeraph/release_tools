import re
import subprocess

def command_exists(cmd):
    return subprocess.run(f"command -v {cmd}", shell=True, capture_output=True, text=True).returncode == 0

def run_command(cmd, repo=None):
    """Run a shell command and return its output."""
    if repo and cmd[0] == 'gh':
        cmd = ['gh', '-R', repo] + cmd[1:]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{' '.join(cmd)}': {e}")
        print('command output stderr:')
        print(e.stderr)
        print('command output stdout:')
        print(e.stdout)
        raise Exception(f"Command '{' '.join(cmd)}' failed with exit code {e.returncode}")

def get_release_map(tag, repo=None):
    output = run_command(["gh", "release", "list", "--json", "tagName", "-q", ".[].tagName"], repo=repo)

    all_releases = output.strip().split('\n')
    pattern = re.compile(f"^{re.escape(tag)}(-extra(?P<num>[0-9]+))?$")

    rel_map = {}
    for r in all_releases:
        match = pattern.match(r)
        if match is None:
            continue
        g = match.groupdict()
        num = g.get('num')
        if num is not None:
            num = int(num)
            if num == 0:
                raise Exception("Release cannot have '-extra0' suffix")
        else:
            num = 0

        rel_map[num] = r

    return rel_map

def get_repo_name_from_gh(repo=None):
    if repo:
        return repo
    try:
        result = run_command(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], repo=repo
        )
        return result.strip()
    except Exception as e:
        raise Exception(f"Error getting repository name: {e}")

def get_asset_names(release, repo=None):
    """Get all asset names for a given release."""
    output = run_command([
        'gh',
        'release',
        'view',
        release,
        '--json',
        'assets',
        '-q',
        '.assets[].name'
    ], repo=repo)
    output = output.strip()
    if not output:
        return []

    return output.split('\n')
