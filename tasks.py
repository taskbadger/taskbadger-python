from invoke import Context, task


@task
def tag_release(c: Context):
    result = c.run("poetry version -s", hide="out")
    version = result.stdout.strip()
    if input(f"Ready to release {version} [y/n]: ") == "y":
        c.run(f"git tag v{version}")
        c.run("git push origin main --tags")


@task
def update_api(c):
    c.run("curl http://localhost:8000/api/schema.json > taskbadger.yaml")
    c.run(
        "cd .. && openapi-python-client update --path taskbadger-python/taskbadger.yaml --config taskbadger-python/generator_config.yml"
    )
