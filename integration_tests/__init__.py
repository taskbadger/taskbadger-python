import os
from pathlib import Path

import pytest

import taskbadger as badger
from taskbadger.systems.celery import CelerySystemIntegration


def _load_config():
    path = Path(__file__).parent.parent / ".env.integration"
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


_load_config()
ORG = os.environ.get("TASKBADGER_ORG", "")
PROJECT = os.environ.get("TASKBADGER_PROJECT", "")
API_KEY = os.environ.get("TASKBADGER_API_KEY", "")

if not ORG or not PROJECT or not API_KEY:
    pytest.fail("Integration test config missing", pytrace=False)
else:
    badger.init(
        os.environ.get("TASKBADGER_ORG", ""),
        os.environ.get("TASKBADGER_PROJECT", ""),
        os.environ.get("TASKBADGER_API_KEY", ""),
        systems=[CelerySystemIntegration()],
    )
    print(
        f"\nIntegration tests configuration:\n    {badger.mug.Badger.current.settings}\n"
    )
