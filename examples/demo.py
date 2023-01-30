import argparse
import os

import taskbadger as tb
from taskbadger import Action, EmailIntegration

if False and __name__ == "__main__":
    tb.init("simongdkelly", "demo-x", "WcMOjV1Z.lkohynNSP2ymjupqQAfKs2bdJ30FsJbf")

    # from taskbadger.sdk import _init

    # _init("http://localhost:8000", "test-9", "test-p", "hDesdY4p.gQPUJeHdPYnrCARYrUoggHmfm9rYpniu")
    # t = create_task("test", value=5, data={"custom": "test"}, actions=[
    #     Action(integration="email", trigger="success", config=ActionConfig.from_dict({
    #         "to": "simongdkelly@gmail.com"
    #     }))
    # ])
    # print(t.name, t.id)

    t = tb.Task.create("demo")
    t.update(data={"demo_data": "custom"})
    t.pre_processing()
    t.processing()
    t.add_actions([Action("success", EmailIntegration(to="simongdkelly@gmail.com"))])
    t.update_progress(10)
    t.increment_progress(10)
    t.success(100)
    print(t.status, t.value, t.name, t.data)


def main(args):
    tb.init(args.org, args.project, args.key)
    # from taskbadger.sdk import _init
    #
    # _init("http://localhost:8000", args.org, args.project, args.key)
    actions = []
    if args.email:
        actions = [tb.Action("*/10%,success,error", integration=EmailIntegration(to=args.email))]

    task = tb.Task.create(args.task_name, data={"host": os.uname().nodename}, actions=actions)

    context = prepare_migration()

    task.start()
    try:
        perform_migration(context, task)
    except Exception as e:
        task.error(data={"error": str(e)})
    else:
        task.success()


def prepare_migration():
    return {}


def perform_migration(context, task: tb.Task):
    total_items = get_total(context)
    task.set_value_max(total_items)
    for chunk in get_data_chunk(context):
        process_chunk(context, chunk)
        task.increment_progress(len(chunk))


def get_total(context):
    return 100


def get_data_chunk(context):
    yield [1] * 100


def process_chunk(context, chunk):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Demo database migration")
    parser.add_argument("task_name")
    parser.add_argument("-o", "--org", required=True, help="Taskbadger Organization slug")
    parser.add_argument("-p", "--project", required=True, help="Taskbadger Project slug")
    parser.add_argument("-k", "--key", required=True, help="Taskbadger API Key")
    parser.add_argument("-e", "--email")
    args = parser.parse_args()

    main(args)
