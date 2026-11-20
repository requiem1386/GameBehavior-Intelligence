
import re
import urllib.request
import urllib.error

from html import unescape

from django.utils import timezone
from django.utils.html import strip_tags

from players.models import Player


USER_AGENT = (
    "Mozilla/5.0 (compatible; GameBehaviorIntelligence/1.0)"
)


def save_sync_error(player, status, error):
    player.steam_sync_status = status
    player.steam_last_sync = timezone.now()
    player.steam_sync_error = error

    player.save(update_fields=[
        "steam_sync_status",
        "steam_last_sync",
        "steam_sync_error",
    ])


def fetch_steam_profile(player):
    """
    Fetch public Steam profile information.

    HTTP 429 is recorded as rate_limited.
    No automatic retry is performed.
    """

    url = player.steam_profile_url

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", "ignore")

    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            status = "rate_limited"
            error = "Steam rate limit: HTTP 429"

            retry_after = (exc.headers or {}).get("Retry-After")
            if retry_after:
                error += f" | Retry-After: {retry_after}"

        else:
            status = "failed"
            error = f"HTTP {exc.code}: {exc.reason}"

        save_sync_error(player, status, error)

        return {
            "success": False,
            "status": status,
            "error": error,
        }

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

        save_sync_error(player, "failed", error)

        return {
            "success": False,
            "status": "failed",
            "error": error,
        }

    # Extract username
    name_match = re.search(
        r'<span class="actual_persona_name"[^>]*>(.*?)</span>',
        html,
        re.IGNORECASE | re.DOTALL,
    )

    username = None

    if name_match:
        username = strip_tags(name_match.group(1))
        username = unescape(username).strip()

    # Extract main profile avatar
    avatar_url = None

    avatar_match = re.search(
        r'<div[^>]+class="[^"]*playerAvatar[^"]*"[^>]*>'
        r'.*?<img[^>]+srcset="([^"]+)"',
        html,
        re.IGNORECASE | re.DOTALL,
    )

    if avatar_match:
        avatar_url = unescape(
            avatar_match.group(1).split()[0]
        )

    if not avatar_url:
        avatar_match = re.search(
            r'<div[^>]+class="[^"]*playerAvatar[^"]*"[^>]*>'
            r'.*?<img[^>]+src="([^"]+)"',
            html,
            re.IGNORECASE | re.DOTALL,
        )

        if avatar_match:
            avatar_url = unescape(avatar_match.group(1))

    # Extract profile location
    location_match = re.search(
        r'<div class="[^"]*header_location[^"]*"[^>]*>'
        r'(.*?)</div>',
        html,
        re.IGNORECASE | re.DOTALL,
    )

    location = None

    if location_match:
        location = strip_tags(location_match.group(1))
        location = unescape(location).strip()
        location = re.sub(r"\s+", " ", location)

    # Update only fields that were successfully extracted
    updated_fields = []

    if username:
        player.username = username
        updated_fields.append("username")

    if avatar_url:
        player.avatar_url = avatar_url
        updated_fields.append("avatar_url")

    if location:
        player.location = location
        updated_fields.append("location")

    # Do not report success if nothing useful was extracted.
    if not updated_fields:
        error = (
            "Profile page was fetched, but no usable "
            "profile information could be extracted."
        )

        save_sync_error(player, "failed", error)

        return {
            "success": False,
            "status": "failed",
            "error": error,
        }

    # Successful profile fetch
    player.steam_sync_status = "success"
    player.steam_last_sync = timezone.now()
    player.steam_sync_error = None

    updated_fields.extend([
        "steam_sync_status",
        "steam_last_sync",
        "steam_sync_error",
    ])

    player.save(update_fields=updated_fields)

    return {
        "success": True,
        "status": "success",
        "player_id": player.id,
        "username": player.username,
        "avatar_url": player.avatar_url,
        "location": player.location,
        "updated_fields": updated_fields,
    }
