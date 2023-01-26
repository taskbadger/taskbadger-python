import dataclasses
from typing import List

from _contextvars import ContextVar

from taskbadger import AuthenticatedClient
from taskbadger.api.task_endpoints import task_create, task_update
from taskbadger.models import Action, StatusEnum, Task, TaskData

_local = ContextVar("taskbadger_client")


def init(organization_slug: str, project_slug: str, token: str):
    client = AuthenticatedClient("https://taskbadger.net", token, raise_on_unexpected_status=True)
    settings = Settings(client, organization_slug, project_slug)

    _local.set(settings)


def create_task(
    name: str,
    status: StatusEnum = StatusEnum.PENDING,
    value: int = None,
    data: dict = None,
    actions: List[Action] = None,
) -> Task:
    task = Task(name=name, status=status, value=value)
    if data:
        task.data = TaskData.from_dict(data)
    if actions:
        task.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(json_body=task)
    return task_create.sync(**kwargs)


def update_task(task: Task) -> Task:
    kwargs = _make_args(id=task.id, json_body=task)
    return task_update.sync(**kwargs)


def _make_args(**kwargs):
    settings = _local.get()
    ret_args = dataclasses.asdict(settings)
    ret_args.update(kwargs)
    return ret_args


def _get_settings():
    return _local.get()


@dataclasses.dataclass
class Settings:
    client: AuthenticatedClient
    organization_slug: str
    project_slug: str


if __name__ == "__main__":
    init("simongdkelly", "demo-x", "WcMOjV1Z.lkohynNSP2ymjupqQAfKs2bdJ30FsJbf")

    # t = create_task("test", value=5, data={"custom": "test"}, actions=[
    #     Action(integration="email", trigger="success", config=ActionConfig.from_dict({
    #         "to": "simongdkelly@gmail.com"
    #     }))
    # ])
    # print(t.name, t.id)

    t = update_task(Task(id="e9f6gAUcNsjN8fBPC4fxyFCRzC", name="test", value=100, status=StatusEnum.SUCCESS))
    print(t.status, t.value)

# def main(args):
#     tb = Taskbadger(args.org, args.project, args.key)
#     actions = [EmailAction('*/10%,success,error', to=args.email)] if args.email else []
#     task = tb.create_task('Demo database migration', actions=actions)
#
#     task.pre_processing()
#     context = prepare_migration()
#
#     task.start()
#     try:
#         perform_migration(context, ProgressWrapper(task))
#     except Exception as e:
#         task.error(data={'error': str(e)})
#     else:
#         task.success()
#
#
# def prepare_migration():
#     return {}
#
#
# def perform_migration(context, progress):
#     progress.set_total(get_total(context))
#     for chunk in get_data_chunk(context):
#         process_chunk(context, chunk)
#         progress.increment(len(chunk))
#
#
# def get_total(context):
#     return 100
#
#
# def get_data_chunk(context):
#     return []
#
#
# def process_chunk(context, chunk):
#     pass
#
#
# if __name__ == '__main__':
#     parser = argparse.ArgumentParser("Demo database migration")
#     parser.add_argument('-o', '--org', required=True, help='Taskbadger Organization slug')
#     parser.add_argument('-p', '--project', required=True, help='Taskbadger Project slug')
#     parser.add_argument('-k', '--key', required=True, help='Taskbadger API Key')
#     parser.add_argument('-e', '--email')
#     args = parser.parse_args()
#
#     main(args)
