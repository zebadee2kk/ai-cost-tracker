# Phase 3: Alert Notifications (Email/Webhook) - Technical Specification

**Feature Priority**: P1 (High Priority)  
**Estimated Effort**: 2-3 weeks  
**Dependencies**: None  
**Target Sprint**: 3.2 (Weeks 4-6)

---

## 1. Problem Statement

### User Need
Users need proactive notifications when:
- Monthly costs exceed predefined thresholds
- Usage spikes unexpectedly (anomaly detected)
- Forecasted end-of-month cost exceeds budget
- API sync fails repeatedly

### Current Limitation
- Alerts exist in database but no delivery mechanism
- Users must log in to dashboard to see alerts
- No way to receive urgent notifications
- High risk of budget overruns going unnoticed

### Business Value
- **High**: Prevents unexpected cost overruns
- Increases user engagement and retention
- Enables real-time cost management
- Critical for enterprise users (compliance requirement)
- Competitive differentiator

---

## 2. Email Service Comparison

### Provider Analysis

#### SendGrid (Recommended ✅)
**Pricing**:
- Free: 100 emails/day forever
- Essentials: $20/month (40,000 emails)

**Pros**:
- Excellent deliverability (>95%)
- Easy API integration
- Rich template system
- Real-time analytics
- Generous free tier

**Cons**:
- Free tier limited to 100/day
- Requires verification for custom domains

**Python Integration**:
```python
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='alerts@ai-cost-tracker.com',
    to_emails='user@example.com',
    subject='Cost Alert: Threshold Exceeded',
    html_content='<p>Your monthly cost has exceeded $100</p>'
)

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
response = sg.send(message)
```

---

#### Amazon SES
**Pricing**:
- Free: 62,000 emails/month (first 12 months)
- After: $0.10 per 1,000 emails

**Pros**:
- Most cost-effective at scale
- AWS integration
- High throughput

**Cons**:
- Requires AWS account setup
- More complex authentication (IAM)
- Requires domain verification
- Free tier expires after 12 months

**Verdict**: Better for high-volume use cases (>100k emails/month)

---

#### Mailgun
**Pricing**:
- Trial: 5,000 emails/month (3 months)
- Foundation: $35/month (50,000 emails)

**Pros**:
- Developer-friendly API
- Good deliverability
- Email validation features

**Cons**:
- Trial limited to 3 months
- More expensive than competitors

**Verdict**: Good alternative to SendGrid

---

### Recommendation Matrix

| Use Case | Recommended Service | Reason |
|----------|---------------------|--------|
| **Phase 3 MVP** | SendGrid | 100 emails/day sufficient, best deliverability |
| **Enterprise** | Amazon SES | Cost-effective at scale, AWS integration |
| **Self-hosted** | SMTP (Postfix) | Full control, no external dependencies |

**For Phase 3**: **SendGrid** ✅

---

## 3. Webhook Integration Patterns

### Slack Incoming Webhooks

**Setup**:
1. Go to Slack App Directory → Incoming Webhooks
2. Choose channel → Generate webhook URL
3. Store URL encrypted in database

**Message Format** (Blocks API):
```python
import requests
import json

def send_slack_alert(webhook_url, account_name, current_cost, threshold, threshold_percentage):
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 AI Cost Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Account:*\n{account_name}"},
                    {"type": "mrkdwn", "text": f"*Service:*\nChatGPT"},
                    {"type": "mrkdwn", "text": f"*Current Cost:*\n${current_cost:.2f}"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n${threshold:.2f}"},
                    {"type": "mrkdwn", "text": f"*Exceeded By:*\n{threshold_percentage:.1f}%"},
                    {"type": "mrkdwn", "text": f"*Alert Level:*\n{'CRITICAL' if threshold_percentage > 20 else 'WARNING'}"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Triggered at <!date^{int(time.time())}^{{date_short}} {{time}}|now>"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Dashboard"},
                        "url": "https://your-app.com/dashboard",
                        "style": "primary"
                    }
                ]
            }
        ]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200
```

---

### Discord Webhooks

**Setup**:
1. Server Settings → Integrations → Webhooks → New Webhook
2. Choose channel → Copy webhook URL

**Message Format** (Embeds):
```python
def send_discord_alert(webhook_url, account_name, current_cost, threshold):
    payload = {
        "username": "AI Cost Tracker",
        "avatar_url": "https://example.com/logo.png",
        "embeds": [{
            "title": "🚨 Cost Alert",
            "description": f"Your **{account_name}** account has exceeded its cost threshold.",
            "color": 15158332,  # Red color
            "fields": [
                {"name": "Current Cost", "value": f"${current_cost:.2f}", "inline": True},
                {"name": "Threshold", "value": f"${threshold:.2f}", "inline": True},
                {"name": "Account", "value": account_name, "inline": True}
            ],
            "footer": {
                "text": "AI Cost Tracker",
                "icon_url": "https://example.com/icon.png"
            },
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 204
```

---

### Microsoft Teams Webhooks

**Setup**:
1. Teams → Channel → Connectors → Incoming Webhook
2. Name webhook → Create → Copy URL

**Message Format** (Adaptive Cards):
```python
def send_teams_alert(webhook_url, account_name, current_cost, threshold):
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "FF0000",
        "summary": "AI Cost Alert",
        "sections": [{
            "activityTitle": "🚨 Cost Threshold Exceeded",
            "activitySubtitle": f"Account: {account_name}",
            "facts": [
                {"name": "Current Cost:", "value": f"${current_cost:.2f}"},
                {"name": "Threshold:", "value": f"${threshold:.2f}"},
                {"name": "Exceeded By:", "value": f"{((current_cost / threshold - 1) * 100):.1f}%"}
            ],
            "markdown": True
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View Dashboard",
            "targets": [{
                "os": "default",
                "uri": "https://your-app.com/dashboard"
            }]
        }]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200
```

---

## 4. Architecture

### System Design

```
┌───────────────────────────────────────────────────┐
│       APScheduler (runs hourly)                   │
│  check_all_thresholds()                          │
└───────────────────────┬──────────────────────────┘
                        │
                        │ For each account
                        │
┌───────────────────────▼──────────────────────────┐
│       Alert Evaluation Logic                      │
│  - Check current month cost vs. threshold        │
│  - Check rate limiting (last alert time)         │
│  - Determine alert level (warning/critical)      │
└───────────────────────┬──────────────────────────┘
                        │ Threshold exceeded?
                        │
┌───────────────────────▼──────────────────────────┐
│       NotificationService (factory)               │
│  - Get user notification preferences             │
│  - Instantiate appropriate services              │
└───────────────────────┬──────────────────────────┘
                        │
       ┌────────────────┼─────────────────┐
       │                │                   │
┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│EmailService│ │WebhookService│ │SmsService │
│ (SendGrid) │ │(Slack/Discord)│ │(Optional) │
└─────────────┘ └──────────────┘ └────────────┘
```

### Database Schema

#### `notification_preferences` table
```sql
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    email_enabled BOOLEAN DEFAULT TRUE,
    email_address VARCHAR(255),
    webhook_enabled BOOLEAN DEFAULT FALSE,
    webhook_url_encrypted TEXT,
    webhook_type VARCHAR(50), -- 'slack', 'discord', 'teams', 'custom'
    alert_levels VARCHAR(100)[], -- ['warning', 'critical', 'emergency']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);
```

#### `alert_history` table
```sql
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    notification_type VARCHAR(50), -- 'email', 'webhook_slack', 'webhook_discord'
    sent_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50), -- 'sent', 'failed', 'rate_limited'
    error_message TEXT,
    INDEX idx_alert_user (alert_id, user_id),
    INDEX idx_sent_at (sent_at)
);
```

---

## 5. API Endpoints

### Notification Preferences

#### `GET /api/notifications/preferences`
Get user's notification settings

**Response**:
```json
{
  "email_enabled": true,
  "email_address": "user@example.com",
  "webhook_enabled": true,
  "webhook_type": "slack",
  "webhook_url": "https://hooks.slack.com/services/...",
  "alert_levels": ["warning", "critical"]
}
```

#### `PUT /api/notifications/preferences`
Update notification settings

**Request**:
```json
{
  "email_enabled": true,
  "email_address": "newemail@example.com",
  "webhook_enabled": true,
  "webhook_type": "discord",
  "webhook_url": "https://discord.com/api/webhooks/...",
  "alert_levels": ["critical", "emergency"]
}
```

#### `POST /api/notifications/test`
Send test notification

**Request**:
```json
{
  "type": "email" // or "webhook"
}
```

### Alert History

#### `GET /api/notifications/history`
Get notification delivery history

**Response**:
```json
{
  "notifications": [
    {
      "id": 123,
      "alert": {
        "id": 45,
        "type": "threshold_exceeded",
        "message": "Monthly cost exceeded $100"
      },
      "type": "email",
      "sent_at": "2026-02-25T14:30:00Z",
      "status": "sent"
    }
  ]
}
```

---

## 6. Implementation Details

### Alert Threshold Levels

| Level | Threshold | Color | Icon | Rate Limit |
|-------|-----------|-------|------|------------|
| **Warning** | 70-89% | Yellow | ⚠️ | 1/day |
| **Critical** | 90-99% | Orange | 🚨 | 1/6 hours |
| **Emergency** | 100%+ | Red | 🔥 | 1/hour |

### Rate Limiting Logic

```python
from datetime import datetime, timedelta

def should_send_alert(alert_level, last_alert_time):
    """Check if enough time has passed since last alert"""
    if last_alert_time is None:
        return True
    
    rate_limits = {
        'warning': timedelta(days=1),
        'critical': timedelta(hours=6),
        'emergency': timedelta(hours=1)
    }
    
    time_since_last = datetime.utcnow() - last_alert_time
    return time_since_last >= rate_limits.get(alert_level, timedelta(hours=1))
```

---

## 7. Testing Strategy

### Unit Tests

```python
def test_email_service_send(mocker):
    """Test email sending via SendGrid"""
    mock_sg = mocker.patch('sendgrid.SendGridAPIClient.send')
    mock_sg.return_value.status_code = 202
    
    service = EmailService(api_key='test_key')
    result = service.send_alert(
        to='user@example.com',
        subject='Test Alert',
        body='Test message'
    )
    
    assert result is True
    mock_sg.assert_called_once()

def test_webhook_service_slack(mocker):
    """Test Slack webhook delivery"""
    mock_post = mocker.patch('requests.post')
    mock_post.return_value.status_code = 200
    
    service = SlackWebhookService(webhook_url='https://hooks.slack.com/...')
    result = service.send_alert(
        account='Test Account',
        cost=150.00,
        threshold=100.00
    )
    
    assert result is True

def test_rate_limiting():
    """Test alert rate limiting"""
    last_alert = datetime.utcnow() - timedelta(minutes=30)
    
    # Should not send (too soon for warning)
    assert not should_send_alert('warning', last_alert)
    
    # Should send (enough time for critical)
    last_alert_critical = datetime.utcnow() - timedelta(hours=7)
    assert should_send_alert('critical', last_alert_critical)
```

---

## 8. Implementation Effort

| Task | Effort | Notes |
|------|--------|-------|
| **Database migrations** | 1 day | notification_preferences, alert_history tables |
| **Email service integration** | 2 days | SendGrid setup, templates |
| **Webhook services** | 2 days | Slack, Discord, Teams |
| **Backend API endpoints** | 2 days | Preferences CRUD, test notifications |
| **Alert evaluation logic** | 1 day | Threshold checking, rate limiting |
| **Frontend UI** | 2 days | Preferences page, test buttons |
| **Testing** | 2 days | Unit, integration tests |
| **Documentation** | 1 day | User guides |

**Total**: 13 days (2-3 weeks)

---

## 9. Acceptance Criteria

- ✅ Users receive email alerts when thresholds exceeded
- ✅ Slack notifications work correctly
- ✅ Discord notifications work correctly
- ✅ Teams notifications work correctly
- ✅ Rate limiting prevents spam
- ✅ Test notification button functional
- ✅ Alert history visible in dashboard
- ✅ Webhook URLs stored encrypted
- ✅ >80% test coverage
- ✅ Documentation complete

---

**Status**: ✅ Ready for Implementation  
**Assigned To**: TBD  
**Sprint**: 3.2 (Weeks 4-6)
