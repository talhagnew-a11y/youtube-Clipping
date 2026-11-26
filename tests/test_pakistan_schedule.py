import sys
sys.dont_write_bytecode = True
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / 'payload/venv/Lib/site-packages/shortsflow/schedule.py'
spec = importlib.util.spec_from_file_location('schedule_under_test', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        assert tz == timezone.utc, 'Scheduling must not depend on Windows local timezone'
        return datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)

with patch.object(module, 'datetime', Clock):
    assert module.pakistan_now() == datetime(2026, 11, 26, 17, 0)
    assert module.parse_when('2026-11-27 09:30:00') == datetime(2026, 11, 27, 9, 30)
    assert module.parse_when('in 2h') == datetime(2026, 11, 26, 19, 0)
    assert module.parse_when('09:00') == datetime(2026, 11, 27, 9, 0)
    with patch.object(module, 'jobs', return_value=[{'at':'2026-11-26 16:59'}, {'at':'2026-11-26 17:01'}]):
        assert module.due('unused') == [{'at':'2026-11-26 16:59'}]
print('PASS: UTC+5 independent of system timezone, calendar seconds, relative time compatibility, missed jobs')
