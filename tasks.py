from invoke import task


@task
def update_api(c):
    c.run(
        "cd .. && openapi-python-client update --path taskbadger-python/taskbadger.yaml --config taskbadger-python/generator_config.yml"
    )
