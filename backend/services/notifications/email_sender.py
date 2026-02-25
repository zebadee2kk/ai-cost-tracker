"""SendGrid email sender for AI Cost Tracker alert notifications."""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Subject-line prefixes by alert level
_LEVEL_EMOJI = {
    "warning": "[WARNING]",
    "critical": "[CRITICAL]",
    "emergency": "[EMERGENCY]",
}


def _render_budget_html(alert_data: Dict[str, Any]) -> str:
    level = alert_data.get("level", "warning")
    header_color = {
        "emergency": "#f44336",
        "critical": "#ff9800",
        "warning": "#ffc107",
    }.get(level, "#ffc107")
    border_color = header_color
    level_label = level.title()
    account_name = alert_data.get("account_name", "Unknown")
    current_cost = float(alert_data.get("current_cost", 0))
    threshold = float(alert_data.get("threshold", 1))
    pct = (current_cost / threshold * 100) if threshold else 0
    message = alert_data.get("message", "")
    verb = "exceeded" if level == "emergency" else "reached"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background: {header_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .content {{ background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }}
  .alert-box {{ background: white; padding: 15px; border-left: 4px solid {border_color}; margin: 15px 0; }}
  .alert-box ul {{ margin: 8px 0; padding-left: 20px; }}
  .button {{ display: inline-block; padding: 12px 24px; background: #2196F3; color: white;
             text-decoration: none; border-radius: 4px; margin: 15px 0; }}
  .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Budget Alert – {level_label}</h1>
    </div>
    <div class="content">
      <p>Hi there,</p>
      <p>Your AI usage for <strong>{account_name}</strong> has {verb} the {level_label} threshold.</p>
      <div class="alert-box">
        <h3>Alert Details</h3>
        <ul>
          <li><strong>Account:</strong> {account_name}</li>
          <li><strong>Current Cost:</strong> ${current_cost:.2f}</li>
          <li><strong>Budget Threshold:</strong> ${threshold:.2f}</li>
          <li><strong>Percentage Used:</strong> {pct:.1f}%</li>
        </ul>
      </div>
      <p>{message}</p>
      <a href="https://ai-cost-tracker.com/dashboard" class="button">View Dashboard</a>
      <p style="margin-top:30px;font-size:14px;color:#666;">
        <strong>What you can do:</strong><br>
        &bull; Review your recent usage patterns<br>
        &bull; Adjust your budget threshold if needed<br>
        &bull; Consider optimizing API calls<br>
        &bull; Set up additional alerts for early warnings
      </p>
    </div>
    <div class="footer">
      <p>AI Cost Tracker | <a href="%unsubscribe%">Unsubscribe</a></p>
      <p>You&apos;re receiving this because you have alert notifications enabled.</p>
    </div>
  </div>
</body>
</html>"""


def _render_anomaly_html(alert_data: Dict[str, Any]) -> str:
    account_name = alert_data.get("account_name", "Unknown")
    message = alert_data.get("message", "")
    current_cost = float(alert_data.get("current_cost", 0))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background: #9c27b0; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .content {{ background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }}
  .alert-box {{ background: white; padding: 15px; border-left: 4px solid #9c27b0; margin: 15px 0; }}
  .alert-box ul {{ margin: 8px 0; padding-left: 20px; }}
  .button {{ display: inline-block; padding: 12px 24px; background: #2196F3; color: white;
             text-decoration: none; border-radius: 4px; margin: 15px 0; }}
  .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Unusual Usage Detected</h1>
    </div>
    <div class="content">
      <p>Hi there,</p>
      <p>We detected unusual activity for <strong>{account_name}</strong>.</p>
      <div class="alert-box">
        <h3>Anomaly Details</h3>
        <ul>
          <li><strong>Account:</strong> {account_name}</li>
          <li><strong>Current Cost:</strong> ${current_cost:.2f}</li>
        </ul>
        <p>{message}</p>
      </div>
      <a href="https://ai-cost-tracker.com/dashboard" class="button">View Dashboard</a>
    </div>
    <div class="footer">
      <p>AI Cost Tracker | <a href="%unsubscribe%">Unsubscribe</a></p>
      <p>You&apos;re receiving this because you have alert notifications enabled.</p>
    </div>
  </div>
</body>
</html>"""


def _render_system_html(alert_data: Dict[str, Any]) -> str:
    message = alert_data.get("message", "")
    account_name = alert_data.get("account_name", "")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background: #607d8b; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .content {{ background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }}
  .alert-box {{ background: white; padding: 15px; border-left: 4px solid #607d8b; margin: 15px 0; }}
  .button {{ display: inline-block; padding: 12px 24px; background: #2196F3; color: white;
             text-decoration: none; border-radius: 4px; margin: 15px 0; }}
  .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>System Alert</h1>
    </div>
    <div class="content">
      <p>Hi there,</p>
      {'<p>Account: <strong>' + account_name + '</strong></p>' if account_name else ''}
      <div class="alert-box">
        <p>{message}</p>
      </div>
      <a href="https://ai-cost-tracker.com/dashboard" class="button">View Dashboard</a>
    </div>
    <div class="footer">
      <p>AI Cost Tracker | <a href="%unsubscribe%">Unsubscribe</a></p>
      <p>You&apos;re receiving this because you have alert notifications enabled.</p>
    </div>
  </div>
</body>
</html>"""


_RENDERERS = {
    "budget": _render_budget_html,
    "anomaly": _render_anomaly_html,
    "system": _render_system_html,
}


class EmailSender:
    """Sends alert notification emails via SendGrid.

    Args:
        api_key: SendGrid API key.
        from_email: Sender email address.
        from_name: Sender display name shown in email clients.
    """

    def __init__(self, api_key: str, from_email: str, from_name: str):
        # Import lazily so the package is only required in production.
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Email as SGEmail

            self.client = SendGridAPIClient(api_key)
            self._sg_from = SGEmail(from_email, from_name)
        except ImportError:
            self.client = None
            self._sg_from = None
            logger.warning(
                "sendgrid package not installed – EmailSender will be non-functional. "
                "Install with: pip install sendgrid"
            )

        self.from_email = from_email
        self.from_name = from_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_alert(self, to_email: str, alert_data: Dict[str, Any]) -> bool:
        """Send an alert notification email.

        Args:
            to_email: Recipient email address.
            alert_data: Dict with keys:
                - type: 'budget' | 'anomaly' | 'system'
                - level: 'warning' | 'critical' | 'emergency'
                - account_name: str
                - current_cost: float
                - threshold: float
                - message: str

        Returns:
            True if the email was accepted by SendGrid.
        """
        if self.client is None:
            logger.error("SendGrid client not initialised – cannot send email.")
            return False

        try:
            from sendgrid.helpers.mail import Mail, To, Content

            html_content = self._render_html(alert_data)
            subject = self._build_subject(alert_data)

            mail = Mail(
                from_email=self._sg_from,
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            response = self.client.send(mail)

            if response.status_code in (200, 201, 202):
                logger.info("Email sent to %s (status %s)", to_email, response.status_code)
                return True

            logger.error(
                "Email send failed: status=%s body=%s",
                response.status_code,
                response.body,
            )
            return False

        except Exception:
            logger.exception("Unexpected error sending email to %s", to_email)
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_subject(self, alert_data: Dict[str, Any]) -> str:
        """Build an email subject line from alert metadata."""
        level = alert_data.get("level", "warning")
        alert_type = alert_data.get("type", "system")
        prefix = _LEVEL_EMOJI.get(level, "[ALERT]")
        account_name = alert_data.get("account_name", "")

        if alert_type == "budget":
            return f"{prefix} AI Cost Alert: {account_name} – {level.title()}"
        if alert_type == "anomaly":
            return f"{prefix} Unusual Usage Detected: {account_name}"
        # system
        return f"{prefix} System Alert: {alert_data.get('message', '')[:60]}"

    def _render_html(self, alert_data: Dict[str, Any]) -> str:
        """Render the HTML body for the given alert type."""
        alert_type = alert_data.get("type", "system")
        renderer = _RENDERERS.get(alert_type, _render_system_html)
        return renderer(alert_data)
