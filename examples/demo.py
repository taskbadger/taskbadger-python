import argparse
import os

import taskbadger as tb
from examples.migration_utils import (
    get_data_chunks,
    get_total,
    prepare_migration,
    process_chunk,
)
from taskbadger import EmailIntegration


def main(args):
    tb.init(args.org, args.project, args.key)
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


def perform_migration(context, task: tb.Task):
    total_items = get_total(context)
    task.set_value_max(total_items)
    for chunk in get_data_chunks(context):
        process_chunk(context, chunk)
        task.increment_progress(len(chunk))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Demo database migration")
    parser.add_argument("task_name")
    parser.add_argument("-o", "--org", required=True, help="Taskbadger Organization slug")
    parser.add_argument("-p", "--project", required=True, help="Taskbadger Project slug")
    parser.add_argument("-k", "--key", required=True, help="Taskbadger API Key")
    parser.add_argument("-e", "--email")
    args = parser.parse_args()

    main(args)
