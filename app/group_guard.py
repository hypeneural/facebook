"""Pure URL matching for authorized Facebook group navigation."""
from urllib.parse import urlsplit
import re

GROUP_PATH = re.compile(r"^/groups/([A-Za-z0-9_.-]{2,150})(?:/|$)")
HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}

def group_id_from_url(url):
    try:
        item = urlsplit(url or "")
        if item.scheme != "https" or item.hostname not in HOSTS:
            return None
        if item.username or item.password or item.port:
            return None
        match = GROUP_PATH.match(item.path)
        return match.group(1) if match else None
    except (TypeError, ValueError):
        return None

def destination_state(current, expected=None):
    try:
        item = urlsplit(current or "")
        valid = item.scheme == "https" and item.hostname in HOSTS and not item.port and not item.username and not item.password
    except (TypeError, ValueError):
        return {"state": "OUTSIDE_FACEBOOK", "group_id": None, "destination_verified": False}
    if not valid:
        return {"state": "OUTSIDE_FACEBOOK", "group_id": None, "destination_verified": False}
    path = (item.path or "/").lower()
    if path.startswith(("/login", "/checkpoint", "/recover")):
        return {"state": "AUTH_OR_CHECKPOINT", "group_id": None, "destination_verified": False}
    actual = group_id_from_url(current)
    wanted = group_id_from_url(expected) if expected else None
    if actual is None:
        return {"state": "NOT_ON_GROUP", "group_id": None, "destination_verified": False}
    if wanted and actual != wanted:
        return {"state": "GROUP_MISMATCH", "group_id": actual, "destination_verified": False}
    return {"state": "GROUP_CONFIRMED", "group_id": actual, "destination_verified": True}
