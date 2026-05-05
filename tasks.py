from pathlib import Path

import tomlkit
from invoke import Context, task

PYPROJECT = Path(__file__).parent / "pyproject.toml"


@task
def tag_release(c: Context):
    version = _get_version()
    bump_key = input(f"Current version: {version}. Bump? [1: major, 2: minor, 3: patch / n]")
    if bump_key in ("1", "2", "3"):
        bump = {"1": "major", "2": "minor", "3": "patch"}[bump_key]
        version = _bump_version(bump)
        c.run("git add pyproject.toml")
        c.run(f"git commit -m 'Bump version to {version}'")

    if input(f"\nReady to release version {version}? [y/n]") == "y":
        c.run(f"git tag v{version}")
        c.run("git push origin main --tags")

        print("Check https://github.com/taskbadger/taskbadger-python/actions/workflows/release.yml for release build.")
        print("Check https://github.com/taskbadger/taskbadger-python/releases and publish the release.")


@task
def update_api(c, local=False):
    if not local:
        c.run("curl http://localhost:8000/api/schema.json > taskbadger.yaml")
    c.run(
        "openapi-python-client generate --meta=none --path taskbadger.yaml "
        "--config generator_config.yml --overwrite "
        "--output-path taskbadger/internal"
    )


def _get_version() -> str:
    doc = tomlkit.parse(PYPROJECT.read_text())
    return doc["project"]["version"]


def _bump_version(part: str) -> str:
    doc = tomlkit.parse(PYPROJECT.read_text())
    major, minor, patch = (int(x) for x in doc["project"]["version"].split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"unknown bump part: {part}")
    new = f"{major}.{minor}.{patch}"
    doc["project"]["version"] = new
    PYPROJECT.write_text(tomlkit.dumps(doc))
    return new
