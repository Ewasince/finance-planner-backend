from __future__ import annotations

from datetime import datetime
from typing import Final

import pytz


DEFAULT_TIME: Final[datetime] = datetime(2025, 11, 1, tzinfo=pytz.utc)
DEFAULT_TIME_WITH_OFFSET: Final[datetime] = datetime(2025, 12, 1, tzinfo=pytz.utc)
MAIN_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000000"
SECOND_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000001"
THIRD_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000002"
OTHER_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000003"
