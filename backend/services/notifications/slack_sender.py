"""Slack incoming-webhook sender for AI Cost Tracker alert notifications."""
import logging
import time
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)

_LEVEL_COLORS = {
    "warning": "#FFC107",
    "critical": "#FF9800",
    "emergency": "#F44336",
}

_LEVEL_EMOJI = {
    "warning": ":large_yellow_circle:",
    "critical": ":large_orange_circle:",
    "emergency": ":red_circle:",
}


class SlackSender:
    """Posts alert notifications to a Slack channel via an Incoming Webhook.

    Slack returns HTTP 200 with body ``ok`` on success.

    Args:
        timeout: Request timeout in seconds (default 10).
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_alert(self, webhook_url: str, alert_data: Dict[str, Any]) -> bool:
        """Send an alert message to Slack.

        Args:
            webhook_url: Slack incoming-webhook URL.
            alert_data: Dict with keys:
                - type: 'budget' | 'anomaly' | 'system'
                - level: 'warning' | 'critical' | 'emergency'
                - account_name: str
                - current_cost: float
                - threshold: float
                - message: str
                - timestamp: (optional) Unix timestamp for attachment footer.

        Returns:
            True if Slack accepted the message.
        """
        try:
            payload = self._build_payload(alert_data)
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200 and response.text == "ok":
                logger.info("Slack notification sent successfully")
                return True

            logger.error(
                "Slack notification failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            return False

        except requests.Timeout:
            logger.error("Slack notification timed out after %ss", self.timeout)
            return False
        except Exception:
            logger.exception("Unexpected error sending Slack notification")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_payload(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construct the Slack Block Kit payload for an alert."""
        level = alert_data.get("level", "warning")
        alert_type = alert_data.get("type", "system")
        account_name = alert_data.get("account_name", "Unknown")
        current_cost = float(alert_data.get("current_cost", 0))
        threshold = float(alert_data.get("threshold", 0))
        message = alert_data.get("message", "")
        emoji = _LEVEL_EMOJI.get(level, ":warning:")
        color = _LEVEL_COLORS.get(level, "#999999")
        ts = int(alert_data.get("timestamp", time.time()))

        header_text = f"{emoji} AI Cost Alert – {level.title()}"
        if alert_type == "anomaly":
            header_text = f"{emoji} Unusual Usage Detected"
        elif alert_type == "system":
            header_text = f"{emoji} System Alert"

        fields = [
            {"type": "mrkdwn", "text": f"*Account:*\n{account_name}"},
            {"type": "mrkdwn", "text": f"*Level:*\n{level.title()}"},
        ]

        if alert_type == "budget":
            pct = (current_cost / threshold * 100) if threshold else 0
            fields += [
                {"type": "mrkdwn", "text": f"*Current Cost:*\n${current_cost:.2f}"},
                {"type": "mrkdwn", "text": f"*Threshold:*\n${threshold:.2f}"},
                {"type": "mrkdwn", "text": f"*Used:*\n{pct:.1f}%"},
            ]
        elif alert_type == "anomaly":
            fields.append(
                {"type": "mrkdwn", "text": f"*Current Cost:*\n${current_cost:.2f}"}
            )

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text, "emoji": True},
            },
            {"type": "section", "fields": fields},
        ]

        if message:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                }
            )

        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Dashboard"},
                        "url": "https://ai-cost-tracker.com/dashboard",
                        "style": "primary",
                    }
                ],
            }
        )

        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "footer": "AI Cost Tracker",
                    "ts": ts,
                }
            ],
        }
