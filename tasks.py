from invoke import Context, task


@task
def tag_release(c: Context):
    version = _get_version(c)
    bump_key = input("Current version: {version}. Bump? [1: major, 2: minor, 3: patch / n]")
    if bump_key in ("1", "2", "3"):
        bump = {"1": "major", "2": "minor", "3": "patch"}.get(bump_key)

        c.run(f"poetry version {bump}")
        version = _get_version(c)
        c.run("git add pyproject.toml")
        c.run(f"git commit -m 'Bump version to {version}'")

    if input(f"\nReady to release version {version}? [y/n]") == "y":
        c.run(f"git tag v{version}")
        c.run("git push origin main --tags")

        print("Check https://github.com/taskbadger/taskbadger-python/actions/workflows/release.yml for release build.")
        print("Check https://github.com/taskbadger/taskbadger-python/releases and publish the release.")


def _get_version(c):
    version = c.run("poetry version -s", hide="out").stdout.strip()
    return version


@task
def update_api(c, local=False):
    if not local:
        c.run("curl http://localhost:8000/api/schema.json > taskbadger.yaml")
    c.run(
        "cd .. && openapi-python-client update --path taskbadger-python/taskbadger.yaml --config taskbadger-python/generator_config.yml"
    )
