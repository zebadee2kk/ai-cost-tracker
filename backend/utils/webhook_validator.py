"""Webhook URL validation utilities.

Enforces strict allowlists for supported webhook providers to prevent SSRF
attacks where an attacker could coerce the backend into issuing requests to
arbitrary URLs including internal network targets.

Each validator:
- Requires the ``https`` scheme.
- Checks the hostname against an allowlist of official webhook domains.
- Checks the URL path prefix to confirm it is a valid webhook path.
"""
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Allowed webhook hosts and path prefixes per provider
# ---------------------------------------------------------------------------

_SLACK_HOSTS = frozenset({"hooks.slack.com"})
_SLACK_PATH_PREFIX = "/services/"

_DISCORD_HOSTS = frozenset({"discord.com", "discordapp.com"})
_DISCORD_PATH_PREFIX = "/api/webhooks/"

_TEAMS_HOST_SUFFIX = ".webhook.office.com"


# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------

def validate_slack_webhook(url: str) -> bool:
    """Return True only for a valid Slack incoming-webhook URL.

    Valid form: ``https://hooks.slack.com/services/<T>/<B>/<token>``
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname in _SLACK_HOSTS
        and parsed.path.startswith(_SLACK_PATH_PREFIX)
    )


def validate_discord_webhook(url: str) -> bool:
    """Return True only for a valid Discord webhook URL.

    Valid form: ``https://discord.com/api/webhooks/<id>/<token>``
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname in _DISCORD_HOSTS
        and parsed.path.startswith(_DISCORD_PATH_PREFIX)
    )


def validate_teams_webhook(url: str) -> bool:
    """Return True only for a valid Microsoft Teams webhook URL.

    Valid form: ``https://<tenant>.webhook.office.com/...``
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    hostname = parsed.hostname or ""
    return (
        parsed.scheme == "https"
        and hostname.endswith(_TEAMS_HOST_SUFFIX)
        and len(hostname) > len(_TEAMS_HOST_SUFFIX)  # must have a subdomain
    )


# ---------------------------------------------------------------------------
# Channel-dispatch helper
# ---------------------------------------------------------------------------

_VALIDATORS = {
    "slack": validate_slack_webhook,
    "discord": validate_discord_webhook,
    "teams": validate_teams_webhook,
}


def validate_webhook_url(channel: str, url: str) -> bool:
    """Return True if *url* is a valid webhook for *channel*.

    Returns True for non-webhook channels (e.g. ``email``) so callers can
    invoke this unconditionally for any channel.
    """
    validator = _VALIDATORS.get(channel)
    if validator is None:
        # Not a webhook-based channel – no URL to validate
        return True
    return validator(url)
