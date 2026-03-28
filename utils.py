import pytz
from datetime import datetime
import re

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
UTC = pytz.UTC

def parse_datetime_moscow(text: str):
    pattern = r'^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})$'
    match = re.match(pattern, text.strip())
    if not match:
        return None
    day, month, year, hour, minute = map(int, match.groups())
    try:
        naive = datetime(year, month, day, hour, minute)
        moscow_dt = MOSCOW_TZ.localize(naive)
        utc_dt = moscow_dt.astimezone(UTC)
        return utc_dt
    except ValueError:
        return None

def format_datetime_utc_to_moscow(dt: datetime):
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    moscow_dt = dt.astimezone(MOSCOW_TZ)
    return moscow_dt.strftime('%d.%m.%Y %H:%M')
