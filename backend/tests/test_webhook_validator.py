"""Tests for backend/utils/webhook_validator.py.

Covers:
- validate_slack_webhook: valid URL, wrong scheme, wrong host, wrong path prefix
- validate_discord_webhook: valid URL, wrong scheme, wrong host, wrong path prefix
- validate_teams_webhook: valid URL, wrong scheme, no subdomain, wrong suffix
- validate_webhook_url dispatcher: email pass-through, per-channel routing
- SSRF payloads are rejected: http://, localhost, internal IPs, data: URIs
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.webhook_validator import (
    validate_slack_webhook,
    validate_discord_webhook,
    validate_teams_webhook,
    validate_webhook_url,
)


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

class TestValidateSlackWebhook:
    def test_valid_url(self):
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        assert validate_slack_webhook(url) is True

    def test_valid_url_minimal_path(self):
        assert validate_slack_webhook("https://hooks.slack.com/services/abc") is True

    def test_http_scheme_rejected(self):
        assert validate_slack_webhook("http://hooks.slack.com/services/T/B/tok") is False

    def test_wrong_host_rejected(self):
        assert validate_slack_webhook("https://evil.com/services/T/B/tok") is False

    def test_localhost_rejected(self):
        assert validate_slack_webhook("https://localhost/services/T/B/tok") is False

    def test_internal_ip_rejected(self):
        assert validate_slack_webhook("https://192.168.1.1/services/T/B/tok") is False

    def test_wrong_path_prefix_rejected(self):
        assert validate_slack_webhook("https://hooks.slack.com/hooks/T/B/tok") is False

    def test_no_path_rejected(self):
        assert validate_slack_webhook("https://hooks.slack.com/") is False

    def test_empty_string_rejected(self):
        assert validate_slack_webhook("") is False

    def test_data_uri_rejected(self):
        assert validate_slack_webhook("data:text/html,<script>alert(1)</script>") is False

    def test_hooks_slack_subdomain_rejected(self):
        # An attacker-controlled subdomain spoofing the host suffix
        assert validate_slack_webhook("https://evil.hooks.slack.com/services/T/B/tok") is False

    def test_hooks_slack_com_in_path_rejected(self):
        assert validate_slack_webhook("https://evil.com/hooks.slack.com/services/T/B/tok") is False


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

class TestValidateDiscordWebhook:
    def test_valid_discord_com_url(self):
        url = "https://discord.com/api/webhooks/123456789/abcdefghijklmn"
        assert validate_discord_webhook(url) is True

    def test_valid_discordapp_com_url(self):
        url = "https://discordapp.com/api/webhooks/123456789/abcdefghijklmn"
        assert validate_discord_webhook(url) is True

    def test_http_scheme_rejected(self):
        assert validate_discord_webhook("http://discord.com/api/webhooks/1/tok") is False

    def test_wrong_host_rejected(self):
        assert validate_discord_webhook("https://evil.com/api/webhooks/1/tok") is False

    def test_localhost_rejected(self):
        assert validate_discord_webhook("https://localhost/api/webhooks/1/tok") is False

    def test_wrong_path_prefix_rejected(self):
        assert validate_discord_webhook("https://discord.com/webhooks/1/tok") is False

    def test_empty_string_rejected(self):
        assert validate_discord_webhook("") is False

    def test_internal_ip_rejected(self):
        assert validate_discord_webhook("https://10.0.0.1/api/webhooks/1/tok") is False


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestValidateTeamsWebhook:
    def test_valid_teams_url(self):
        url = "https://myorg.webhook.office.com/webhookb2/abc123/IncomingWebhook/def456"
        assert validate_teams_webhook(url) is True

    def test_http_scheme_rejected(self):
        assert validate_teams_webhook("http://myorg.webhook.office.com/webhookb2/abc") is False

    def test_bare_office_com_rejected(self):
        # Must have a real subdomain before .webhook.office.com
        assert validate_teams_webhook("https://webhook.office.com/webhookb2/abc") is False

    def test_wrong_suffix_rejected(self):
        assert validate_teams_webhook("https://evil.com/webhookb2/abc") is False

    def test_localhost_rejected(self):
        assert validate_teams_webhook("https://localhost/webhookb2/abc") is False

    def test_spoofed_suffix_in_path_rejected(self):
        assert validate_teams_webhook("https://evil.com/.webhook.office.com/webhookb2/abc") is False

    def test_empty_string_rejected(self):
        assert validate_teams_webhook("") is False


# ---------------------------------------------------------------------------
# validate_webhook_url dispatcher
# ---------------------------------------------------------------------------

class TestValidateWebhookUrl:
    def test_email_channel_always_passes(self):
        # Email uses an address, not a webhook URL; no URL validation needed
        assert validate_webhook_url("email", "not-a-url-at-all") is True

    def test_unknown_channel_passes(self):
        assert validate_webhook_url("sms", "anything") is True

    def test_slack_valid_routed_correctly(self):
        assert validate_webhook_url("slack", "https://hooks.slack.com/services/T/B/tok") is True

    def test_slack_invalid_rejected(self):
        assert validate_webhook_url("slack", "https://evil.com/services/T/B/tok") is False

    def test_discord_valid_routed_correctly(self):
        assert validate_webhook_url("discord", "https://discord.com/api/webhooks/1/tok") is True

    def test_discord_invalid_rejected(self):
        assert validate_webhook_url("discord", "http://discord.com/api/webhooks/1/tok") is False

    def test_teams_valid_routed_correctly(self):
        assert validate_webhook_url("teams", "https://x.webhook.office.com/webhookb2/abc") is True

    def test_teams_invalid_rejected(self):
        assert validate_webhook_url("teams", "https://evil.com/webhookb2/abc") is False

    # SSRF payloads
    def test_ssrf_localhost(self):
        assert validate_webhook_url("slack", "https://localhost/services/T/B/tok") is False

    def test_ssrf_internal_ip_169(self):
        # 169.254.x.x – link-local / AWS metadata endpoint
        assert validate_webhook_url("slack", "https://169.254.169.254/services/T/B/tok") is False

    def test_ssrf_internal_ip_172(self):
        assert validate_webhook_url("slack", "https://172.16.0.1/services/T/B/tok") is False

    def test_ssrf_http_scheme(self):
        assert validate_webhook_url("slack", "http://hooks.slack.com/services/T/B/tok") is False
