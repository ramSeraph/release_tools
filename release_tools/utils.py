import re
import subprocess

def get_release_map(tag):
    result = subprocess.run(
        ["gh", "release", "list", "--json", "tagName", "-q", ".[].tagName"],
        capture_output=True,
        text=True,
        check=True,
    )
    all_releases = result.stdout.strip().split('\n')
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


