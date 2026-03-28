import pytz
from datetime import datetime
import re

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def parse_datetime(text: str) -> datetime | None:
    pattern = r'^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})$'
    match = re.match(pattern, text.strip())
    if not match:
        return None
    day, month, year, hour, minute = map(int, match.groups())
    try:
        dt = datetime(year, month, day, hour, minute)
        return MOSCOW_TZ.localize(dt)
    except ValueError:
        return None

def format_datetime(dt: datetime) -> str:
    msk_dt = dt.astimezone(MOSCOW_TZ) if dt.tzinfo else MOSCOW_TZ.localize(dt)
    return msk_dt.strftime('%d.%m.%Y %H:%M')