import datetime

from taskbadger import track


@track(max_runtime=1)
def my_task(arg1, arg2, kwarg1=None, kwarg2="demo"):
    print("Hello from my_task")
    print(f"arg1={arg1}, arg2={arg2}, kwarg1={kwarg1}, kwarg2={kwarg2}")
    return ["Hello from my_task", datetime.datetime.now(datetime.timezone.utc)]


if __name__ == "__main__":
    my_task(1, 2, kwarg1="foo", kwarg2="bar")
