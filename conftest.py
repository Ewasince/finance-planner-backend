from __future__ import annotations

import pytest

from core.bootstrap import bootstrap_dev_data


@pytest.fixture(scope="session")
def bootstrap_db(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        bootstrap_dev_data()
    yield


@pytest.fixture(scope="function")
def fresh_db(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        bootstrap_dev_data()
    yield
