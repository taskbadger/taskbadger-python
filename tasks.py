from invoke import Context, task


@task
def tag_release(c: Context):
    version = _get_version(c)
    if input(f"Ready to release {version}? [y/n]: ") != "y":
        if input("Bump version? [y/n]") != "y":
            return

        bump_key = input("1: major, 2: minor, 3: patch? [1/2/3]:")
        bump = {"1": "major", "2": "minor", "3": "patch"}.get(bump_key)
        if not bump:
            return

        c.run(f"poetry version {bump}")
        version = _get_version(c)
        c.run("git add pyproject.toml")
        c.run(f"git commit -m 'Bump version to {version}'")
        if input(f"New version: {version}. Ready to release? [y/n]") != "y":
            return

    c.run(f"git tag v{version}")
    c.run("git push origin main --tags")


def _get_version(c):
    version = c.run("poetry version -s", hide="out").stdout.strip()
    return version


@task
def update_api(c):
    c.run("curl http://localhost:8000/api/schema.json > taskbadger.yaml")
    c.run(
        "cd .. && openapi-python-client update --path taskbadger-python/taskbadger.yaml --config taskbadger-python/generator_config.yml"
    )
