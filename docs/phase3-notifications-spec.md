# Phase 3: Alert Notifications (Email/Webhook) - Technical Specification

**Created**: February 25, 2026  
**Priority**: P1  
**Effort**: 2-3 weeks  
**Dependencies**: None

---

## 1. Problem Statement

### Business Need
Users need proactive alerts when:
- Monthly spend exceeds budget thresholds
- Usage spikes detected (anomaly)
- API sync failures occur
- Account approaching limits

### Current Limitations
- Alerts only visible in dashboard (reactive)
- No email notifications
- No Slack/Discord/Teams integration
- Users must manually check for problems

### Success Criteria
- >95% alert delivery success rate
- <5 minute delay from threshold breach to notification
- <1% false positive rate
- Zero notification spam (proper rate limiting)

---

## 2. Alert Types

### Budget Threshold Alerts

| Level | Threshold | Color | Priority | Example |
|-------|-----------|-------|----------|----------|
| **Warning** | 70% | 🟡 Yellow | Low | "You've used 70% of your $100 budget" |
| **Critical** | 90% | 🟠 Orange | Medium | "You've used 90% of your $100 budget" |
| **Emergency** | 100% | 🔴 Red | High | "You've exceeded your $100 budget" |

### Anomaly Alerts

- **Usage Spike**: Daily cost >3σ above mean
- **Unusual Pattern**: Request volume spike without cost increase
- **Service Outage**: API sync failure >3 attempts

### System Alerts

- **Sync Failure**: Unable to fetch usage data from provider
- **Auth Error**: API key expired or invalid
- **Rate Limit**: Approaching provider rate limits

---

## 3. Notification Channels

### Email (Primary Channel)

**Providers Comparison**:

| Provider | Free Tier | Cost (50k/mo) | Deliverability | API Ease | Recommendation |
|----------|-----------|---------------|----------------|----------|----------------|
| **SendGrid** | 100/day forever | $20/mo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ **Best Choice** |
| **Amazon SES** | 62k/mo (12 mo) | $5/mo | ⭐⭐⭐⭐ | ⭐⭐⭐ | Best for AWS users |
| **Mailgun** | 5k/mo (3 mo) | $35/mo | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Good alternative |

**Recommendation**: **SendGrid** for best balance of cost, deliverability, and developer experience.

### Webhooks (Secondary Channels)

| Platform | Format | Difficulty | Use Case |
|----------|--------|------------|----------|
| **Slack** | Incoming Webhook + Blocks | Easy | Team notifications |
| **Discord** | Webhook + Embeds | Easy | Community/personal |
| **Microsoft Teams** | Incoming Webhook + Adaptive Cards | Medium | Enterprise teams |
| **Generic Webhook** | Custom JSON | Easy | Custom integrations |

---

## 4. Architecture Design

### System Components

```
┌─────────────────────────────────────────────────┐
│         Alert Generation Service                │
│  (Runs hourly via APScheduler)                  │
│                                                  │
│  1. Check all accounts for threshold breaches   │
│  2. Check for anomalies (Z-score analysis)      │
│  3. Check sync status (last_synced timestamp)   │
│  4. Generate alert records                       │
└───────────────────┬─────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│         Notification Queue                       │
│  (Database table: notification_queue)            │
│                                                  │
│  Fields: alert_id, channel, recipient,           │
│          priority, retry_count, status           │
└───────────────────┬─────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│      Notification Dispatcher Service             │
│  (Runs every 5 minutes via APScheduler)          │
│                                                  │
│  1. Fetch pending notifications                  │
│  2. Check rate limits (per user/channel)         │
│  3. Route to appropriate sender                  │
│  4. Update status (sent/failed/retry)            │
└───────────┬──────────────────────┬───────────────┘
            │                      │
            ↓                      ↓
┌───────────────────┐  ┌───────────────────────┐
│  Email Sender     │  │  Webhook Sender       │
│  (SendGrid API)   │  │  (HTTP POST)          │
│                   │  │                       │
│  - HTML templates │  │  - Slack formatter    │
│  - Retry logic    │  │  - Discord formatter  │
│  - Unsubscribe    │  │  - Teams formatter    │
└───────────────────┘  └───────────────────────┘
```

### Database Schema

```sql
-- Notification preferences table
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL, -- 'email', 'slack', 'discord', 'teams'
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB, -- Channel-specific config (webhook URL, email address)
    alert_types JSONB, -- Which alerts to receive ['budget', 'anomaly', 'system']
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, channel)
);

-- Notification queue table
CREATE TABLE notification_queue (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    recipient TEXT NOT NULL, -- Email address or webhook URL
    priority INTEGER DEFAULT 1, -- 1=low, 2=medium, 3=high
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_status_priority (status, priority DESC)
);

-- Notification history (for analytics)
CREATE TABLE notification_history (
    id SERIAL PRIMARY KEY,
    notification_id INTEGER REFERENCES notification_queue(id),
    channel VARCHAR(50),
    status VARCHAR(20),
    duration_ms INTEGER, -- Time to send
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_created_at (created_at DESC)
);
```

---

## 5. Implementation Details

### Email Service (SendGrid)

#### Setup

```bash
pip install sendgrid
```

#### Configuration

```python
# config.py
import os

class Config:
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@ai-cost-tracker.com')
    SENDGRID_FROM_NAME = os.getenv('SENDGRID_FROM_NAME', 'AI Cost Tracker')
```

#### Email Sender Class

```python
# services/notifications/email_sender.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from jinja2 import Environment, FileSystemLoader
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, api_key, from_email, from_name):
        self.client = SendGridAPIClient(api_key)
        self.from_email = Email(from_email, from_name)
        self.template_env = Environment(loader=FileSystemLoader('templates/emails'))
    
    def send_alert(self, to_email, alert_data):
        """
        Send alert notification email.
        
        Args:
            to_email: Recipient email address
            alert_data: Dict with alert details
                {
                    'type': 'budget' | 'anomaly' | 'system',
                    'level': 'warning' | 'critical' | 'emergency',
                    'account_name': str,
                    'current_cost': float,
                    'threshold': float,
                    'message': str
                }
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Render email template
            template = self.template_env.get_template(f"{alert_data['type']}_alert.html")
            html_content = template.render(**alert_data)
            
            # Build email
            subject = self._get_subject(alert_data)
            mail = Mail(
                from_email=self.from_email,
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            # Add unsubscribe group (required for CAN-SPAM compliance)
            mail.asm = {
                "group_id": 12345,  # Replace with your SendGrid unsubscribe group ID
                "groups_to_display": [12345]
            }
            
            # Send
            response = self.client.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Email send failed: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Email send exception: {str(e)}", exc_info=True)
            return False
    
    def _get_subject(self, alert_data):
        """Generate email subject based on alert type and level."""
        emojis = {
            'warning': '🟡',
            'critical': '🟠',
            'emergency': '🔴'
        }
        emoji = emojis.get(alert_data['level'], '⚠️')
        
        if alert_data['type'] == 'budget':
            return f"{emoji} AI Cost Alert: {alert_data['account_name']} - {alert_data['level'].title()}"
        elif alert_data['type'] == 'anomaly':
            return f"{emoji} Unusual Usage Detected: {alert_data['account_name']}"
        else:
            return f"{emoji} System Alert: {alert_data['message']}"
```

#### Email Templates

```html
<!-- templates/emails/budget_alert.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: {{ level == 'emergency' and '#f44336' or (level == 'critical' and '#ff9800' or '#ffc107') }}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }
        .alert-box { background: white; padding: 15px; border-left: 4px solid {{ level == 'emergency' and '#f44336' or (level == 'critical' and '#ff9800' or '#ffc107') }}; margin: 15px 0; }
        .button { display: inline-block; padding: 12px 24px; background: #2196F3; color: white; text-decoration: none; border-radius: 4px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ level == 'emergency' and '🔴' or (level == 'critical' and '🟠' or '🟡') }} Budget Alert</h1>
        </div>
        <div class="content">
            <p>Hi there,</p>
            <p>Your AI usage for <strong>{{ account_name }}</strong> has {{ level == 'emergency' and 'exceeded' or 'reached' }} the {{ level }} threshold.</p>
            
            <div class="alert-box">
                <h3>Alert Details</h3>
                <ul>
                    <li><strong>Account:</strong> {{ account_name }}</li>
                    <li><strong>Current Cost:</strong> ${{ "%0.2f"|format(current_cost) }}</li>
                    <li><strong>Budget Threshold:</strong> ${{ "%0.2f"|format(threshold) }}</li>
                    <li><strong>Percentage Used:</strong> {{ "%0.1f"|format((current_cost / threshold) * 100) }}%</li>
                </ul>
            </div>
            
            <p>{{ message }}</p>
            
            <a href="https://ai-cost-tracker.com/dashboard" class="button">View Dashboard</a>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                <strong>What you can do:</strong><br>
                • Review your recent usage patterns<br>
                • Adjust your budget threshold if needed<br>
                • Consider optimizing API calls<br>
                • Set up additional alerts for early warnings
            </p>
        </div>
        <div class="footer">
            <p>AI Cost Tracker | <a href="%unsubscribe%">Unsubscribe</a></p>
            <p>You're receiving this because you have alert notifications enabled.</p>
        </div>
    </div>
</body>
</html>
```

---

### Webhook Service

#### Slack Integration

```python
# services/notifications/slack_sender.py
import requests
import logging

logger = logging.getLogger(__name__)

class SlackSender:
    def send_alert(self, webhook_url, alert_data):
        """
        Send alert to Slack using Incoming Webhook.
        
        Args:
            webhook_url: Slack incoming webhook URL
            alert_data: Dict with alert details
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Map alert level to colors
            colors = {
                'warning': '#FFC107',   # Yellow
                'critical': '#FF9800',  # Orange
                'emergency': '#F44336'  # Red
            }
            
            # Build Slack blocks payload
            payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{self._get_emoji(alert_data['level'])} AI Cost Alert"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Account:*\n{alert_data['account_name']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Level:*\n{alert_data['level'].title()}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Current Cost:*\n${alert_data['current_cost']:.2f}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Threshold:*\n${alert_data['threshold']:.2f}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": alert_data['message']
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Dashboard"
                                },
                                "url": "https://ai-cost-tracker.com/dashboard",
                                "style": "primary"
                            }
                        ]
                    }
                ],
                "attachments": [
                    {
                        "color": colors.get(alert_data['level'], '#999'),
                        "footer": "AI Cost Tracker",
                        "ts": int(alert_data.get('timestamp', 0))
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error(f"Slack notification failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack notification exception: {str(e)}", exc_info=True)
            return False
    
    def _get_emoji(self, level):
        return {
            'warning': '🟡',
            'critical': '🟠',
            'emergency': '🔴'
        }.get(level, '⚠️')
```

#### Discord Integration

```python
# services/notifications/discord_sender.py
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordSender:
    def send_alert(self, webhook_url, alert_data):
        """
        Send alert to Discord using Webhook.
        
        Args:
            webhook_url: Discord webhook URL
            alert_data: Dict with alert details
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Map alert level to colors (decimal values)
            colors = {
                'warning': 0xFFC107,   # Yellow
                'critical': 0xFF9800,  # Orange
                'emergency': 0xF44336  # Red
            }
            
            # Build Discord embed payload
            payload = {
                "username": "AI Cost Tracker",
                "avatar_url": "https://ai-cost-tracker.com/logo.png",
                "embeds": [
                    {
                        "title": f"{self._get_emoji(alert_data['level'])} AI Cost Alert",
                        "description": alert_data['message'],
                        "color": colors.get(alert_data['level'], 0x999999),
                        "fields": [
                            {
                                "name": "Account",
                                "value": alert_data['account_name'],
                                "inline": True
                            },
                            {
                                "name": "Level",
                                "value": alert_data['level'].title(),
                                "inline": True
                            },
                            {
                                "name": "Current Cost",
                                "value": f"${alert_data['current_cost']:.2f}",
                                "inline": True
                            },
                            {
                                "name": "Threshold",
                                "value": f"${alert_data['threshold']:.2f}",
                                "inline": True
                            },
                            {
                                "name": "Percentage Used",
                                "value": f"{(alert_data['current_cost'] / alert_data['threshold']) * 100:.1f}%",
                                "inline": True
                            }
                        ],
                        "footer": {
                            "text": "AI Cost Tracker"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:  # Discord returns 204 on success
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord notification failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Discord notification exception: {str(e)}", exc_info=True)
            return False
    
    def _get_emoji(self, level):
        return {
            'warning': '🟡',
            'critical': '🟠',
            'emergency': '🔴'
        }.get(level, '⚠️')
```

---

## 6. Rate Limiting

### Strategy

```python
# services/notifications/rate_limiter.py
from datetime import datetime, timedelta
from models import NotificationHistory

class RateLimiter:
    LIMITS = {
        'email': {'per_hour': 10, 'per_day': 50},
        'slack': {'per_hour': 20, 'per_day': 100},
        'discord': {'per_hour': 20, 'per_day': 100},
        'teams': {'per_hour': 20, 'per_day': 100}
    }
    
    def can_send(self, user_id, channel):
        """
        Check if notification can be sent based on rate limits.
        
        Args:
            user_id: User ID
            channel: Notification channel ('email', 'slack', etc.)
        
        Returns:
            bool: True if within rate limits
        """
        limits = self.LIMITS.get(channel, {'per_hour': 10, 'per_day': 50})
        
        # Check hourly limit
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = NotificationHistory.query.filter(
            NotificationHistory.user_id == user_id,
            NotificationHistory.channel == channel,
            NotificationHistory.created_at >= one_hour_ago
        ).count()
        
        if recent_count >= limits['per_hour']:
            return False
        
        # Check daily limit
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        daily_count = NotificationHistory.query.filter(
            NotificationHistory.user_id == user_id,
            NotificationHistory.channel == channel,
            NotificationHistory.created_at >= one_day_ago
        ).count()
        
        if daily_count >= limits['per_day']:
            return False
        
        return True
```

---

## 7. Frontend Configuration UI

### Notification Settings Page

```jsx
// pages/NotificationSettingsPage.jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';

function NotificationSettingsPage() {
  const [preferences, setPreferences] = useState({
    email: { enabled: false, address: '', alert_types: [] },
    slack: { enabled: false, webhook_url: '', alert_types: [] },
    discord: { enabled: false, webhook_url: '', alert_types: [] }
  });
  
  const alertTypes = [
    { value: 'budget', label: 'Budget Threshold Alerts' },
    { value: 'anomaly', label: 'Usage Anomaly Alerts' },
    { value: 'system', label: 'System & Sync Alerts' }
  ];
  
  useEffect(() => {
    loadPreferences();
  }, []);
  
  const loadPreferences = async () => {
    const response = await api.get('/api/notifications/preferences');
    setPreferences(response.data);
  };
  
  const handleToggle = (channel) => {
    setPreferences(prev => ({
      ...prev,
      [channel]: {
        ...prev[channel],
        enabled: !prev[channel].enabled
      }
    }));
  };
  
  const handleSave = async () => {
    try {
      await api.post('/api/notifications/preferences', preferences);
      alert('Notification preferences saved!');
    } catch (error) {
      alert('Failed to save preferences');
    }
  };
  
  const handleTest = async (channel) => {
    try {
      await api.post(`/api/notifications/test/${channel}`);
      alert(`Test notification sent to ${channel}!`);
    } catch (error) {
      alert(`Failed to send test notification: ${error.message}`);
    }
  };
  
  return (
    <div className="notification-settings">
      <h1>Notification Settings</h1>
      
      {/* Email Settings */}
      <div className="channel-config">
        <div className="channel-header">
          <label>
            <input
              type="checkbox"
              checked={preferences.email.enabled}
              onChange={() => handleToggle('email')}
            />
            📧 Email Notifications
          </label>
        </div>
        
        {preferences.email.enabled && (
          <div className="channel-details">
            <input
              type="email"
              placeholder="your.email@example.com"
              value={preferences.email.address}
              onChange={(e) => setPreferences({
                ...preferences,
                email: { ...preferences.email, address: e.target.value }
              })}
            />
            
            <div className="alert-types">
              <p>Send me alerts for:</p>
              {alertTypes.map(type => (
                <label key={type.value}>
                  <input
                    type="checkbox"
                    checked={preferences.email.alert_types.includes(type.value)}
                    onChange={(e) => {
                      const types = e.target.checked
                        ? [...preferences.email.alert_types, type.value]
                        : preferences.email.alert_types.filter(t => t !== type.value);
                      setPreferences({
                        ...preferences,
                        email: { ...preferences.email, alert_types: types }
                      });
                    }}
                  />
                  {type.label}
                </label>
              ))}
            </div>
            
            <button onClick={() => handleTest('email')}>Send Test Email</button>
          </div>
        )}
      </div>
      
      {/* Slack Settings */}
      <div className="channel-config">
        <div className="channel-header">
          <label>
            <input
              type="checkbox"
              checked={preferences.slack.enabled}
              onChange={() => handleToggle('slack')}
            />
            💬 Slack Notifications
          </label>
        </div>
        
        {preferences.slack.enabled && (
          <div className="channel-details">
            <input
              type="url"
              placeholder="https://hooks.slack.com/services/..."
              value={preferences.slack.webhook_url}
              onChange={(e) => setPreferences({
                ...preferences,
                slack: { ...preferences.slack, webhook_url: e.target.value }
              })}
            />
            <p className="help-text">
              <a href="https://api.slack.com/messaging/webhooks" target="_blank" rel="noopener noreferrer">
                How to create a Slack webhook →
              </a>
            </p>
            
            {/* Alert types selection (same as email) */}
            
            <button onClick={() => handleTest('slack')}>Send Test Message</button>
          </div>
        )}
      </div>
      
      {/* Discord Settings (similar structure) */}
      
      <button className="save-button" onClick={handleSave}>
        Save Notification Preferences
      </button>
    </div>
  );
}

export default NotificationSettingsPage;
```

---

## 8. Testing Strategy

### Unit Tests

```python
# tests/test_email_sender.py
import pytest
from unittest.mock import Mock, patch
from services.notifications.email_sender import EmailSender

def test_email_sender_success():
    sender = EmailSender('test-api-key', 'from@example.com', 'Test')
    
    with patch.object(sender.client, 'send') as mock_send:
        mock_send.return_value = Mock(status_code=202)
        
        alert_data = {
            'type': 'budget',
            'level': 'warning',
            'account_name': 'Test Account',
            'current_cost': 75.00,
            'threshold': 100.00,
            'message': 'Test alert'
        }
        
        result = sender.send_alert('to@example.com', alert_data)
        assert result is True
        assert mock_send.called

def test_email_sender_failure():
    sender = EmailSender('test-api-key', 'from@example.com', 'Test')
    
    with patch.object(sender.client, 'send') as mock_send:
        mock_send.return_value = Mock(status_code=400, body='Bad request')
        
        result = sender.send_alert('to@example.com', {})
        assert result is False
```

### Integration Tests

```python
# tests/test_notification_flow.py
def test_full_notification_flow(client, auth_headers):
    # 1. Configure notification preferences
    prefs = {
        'email': {
            'enabled': True,
            'address': 'test@example.com',
            'alert_types': ['budget']
        }
    }
    response = client.post('/api/notifications/preferences', 
                          json=prefs, 
                          headers=auth_headers)
    assert response.status_code == 200
    
    # 2. Trigger alert condition (exceed budget)
    # ... add usage records that exceed threshold
    
    # 3. Run alert generation job
    from jobs.alert_generator import generate_alerts
    generate_alerts()
    
    # 4. Verify notification was queued
    from models import NotificationQueue
    pending = NotificationQueue.query.filter_by(
        status='pending',
        channel='email'
    ).first()
    assert pending is not None
    
    # 5. Run notification dispatcher
    from jobs.notification_dispatcher import dispatch_notifications
    with patch('services.notifications.email_sender.EmailSender.send_alert') as mock_send:
        mock_send.return_value = True
        dispatch_notifications()
    
    # 6. Verify notification marked as sent
    pending = NotificationQueue.query.get(pending.id)
    assert pending.status == 'sent'
```

---

## 9. Implementation Checklist

### Week 1: Foundation (Days 1-5)
- [ ] Create database migrations (notification_preferences, notification_queue, notification_history)
- [ ] Implement NotificationPreferences model
- [ ] Implement NotificationQueue model
- [ ] Create API endpoints (/api/notifications/preferences GET/POST)
- [ ] Write unit tests for models and endpoints

### Week 2: Email & Webhooks (Days 6-10)
- [ ] Sign up for SendGrid, get API key
- [ ] Implement EmailSender class
- [ ] Create email templates (budget, anomaly, system alerts)
- [ ] Implement SlackSender class
- [ ] Implement DiscordSender class
- [ ] Write unit tests for sender classes
- [ ] Test email delivery end-to-end
- [ ] Test webhook delivery end-to-end

### Week 3: Jobs & Frontend (Days 11-15)
- [ ] Implement alert generation job (runs hourly)
- [ ] Implement notification dispatcher job (runs every 5 min)
- [ ] Add rate limiting logic
- [ ] Create NotificationSettingsPage component
- [ ] Add test notification endpoints
- [ ] Implement retry logic for failed notifications
- [ ] Add notification history view
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Deploy to staging for QA

---

## 10. Success Metrics

### Delivery Rate (30 days post-launch)
- **Target**: >95% successful delivery
- **Measurement**: `(sent_count / total_queued) * 100`

### Response Time
- **Target**: <5 minutes from threshold breach to notification
- **Measurement**: `timestamp(sent) - timestamp(alert_created)`

### False Positive Rate
- **Target**: <1% of users report false alarms
- **Measurement**: User feedback survey + support tickets

### User Adoption
- **Target**: 50% of users enable at least one notification channel
- **Measurement**: Count of users with notification_preferences.enabled = true

---

**Document Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Estimated Effort**: 2-3 weeks  
**Dependencies**: SendGrid account (free tier sufficient)  
**Risks**: Email deliverability (mitigate with SendGrid's high reputation)
