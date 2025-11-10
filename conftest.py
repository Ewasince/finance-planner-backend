from __future__ import annotations

import os

import django
import pytest
from freezegun import freeze_time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from core.bootstrap import bootstrap_dev_data, DEFAULT_TIME


@pytest.fixture(scope="session")
def bootstrap_db(django_db_setup, django_db_blocker):
    with freeze_time(DEFAULT_TIME):
        with django_db_blocker.unblock():
            bootstrap_dev_data()
        yield


@pytest.fixture(scope="function")
def fresh_db(django_db_setup, django_db_blocker):
    with freeze_time(DEFAULT_TIME):
        with django_db_blocker.unblock():
            bootstrap_dev_data()
        yield
