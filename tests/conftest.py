import os
import sys
from pathlib import Path

import django


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "finance_planner"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_planner.core.settings")


django.setup()
