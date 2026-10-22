#!/usr/bin/env python3
"""
Check that every package named in the repo's requirements files is real.

A requirements line naming a package that is not on PyPI is a supply chain
risk: anyone can register that name and their code runs on every
`pip install -r`. Some names also exist on PyPI but are not what the author
meant (the standard library's asyncio and secrets, for example).

    python scripts/check_requirements.py

Exits non-zero if any name is unknown to PyPI or on the list below.
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

# Names that exist on PyPI but should never be installed from there.
WRONG_PACKAGES = {
    "asyncio": "part of the standard library; the PyPI package is a 2015 backport",
    "secrets": "part of the standard library; the PyPI package is unrelated",
    "dataclasses": "part of the standard library since Python 3.7",
    "google-cloud": "deprecated meta package; install a specific google-cloud-* client",
}


def requirement_files():
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    )
    return [
        f
        for f in out.stdout.splitlines()
        if re.search(r"requirements?(-[\w-]+)?\.txt$", f)
    ]


def package_names(path):
    for number, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        name = re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0]
        yield number, name


def exists_on_pypi(name, cache={}):
    if name not in cache:
        url = f"https://pypi.org/pypi/{name}/json"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                cache[name] = json.load(response)["info"]["name"] is not None
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            cache[name] = False
    return cache[name]


def main():
    problems = []
    for path in requirement_files():
        for number, name in package_names(path):
            normalized = re.sub(r"[-_.]+", "-", name).lower()
            if normalized in WRONG_PACKAGES:
                problems.append(
                    f"{path}:{number}: {name}: {WRONG_PACKAGES[normalized]}"
                )
            elif not exists_on_pypi(normalized):
                problems.append(f"{path}:{number}: {name}: not on PyPI")

    for problem in problems:
        print(problem)
    print(
        f"{len(problems)} problem(s)"
        if problems
        else "All requirement names exist on PyPI"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
