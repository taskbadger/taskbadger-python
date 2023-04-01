from invoke import task


@task
def update_api(c):
    c.run("curl http://localhost:8000/api/schema.json > taskbadger.yaml")
    c.run(
        "cd .. && openapi-python-client update --path taskbadger-python/taskbadger.yaml --config taskbadger-python/generator_config.yml"
    )
