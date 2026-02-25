# API Integration Specifications

## Quick Reference: Service API Details

### 1. OpenAI (ChatGPT/Codex/GPT-4)

**API Documentation**: https://platform.openai.com/docs/api-reference/usage

**Authentication**:
```
Authorization: Bearer sk-...
Content-Type: application/json
```

**Key Endpoints**:
- `GET /v1/dashboard/billing/usage` - Usage data for current billing period
- `GET /v1/dashboard/billing/credit_grants` - Credit usage
- `GET /v1/billing/subscription` - Subscription details

**Rate Limits**: 3,500 requests per minute

**Cost Model**:
- GPT-4: ~$0.03/1K input tokens, $0.06/1K output tokens
- GPT-3.5-turbo: ~$0.0005/1K input tokens, $0.0015/1K output tokens
- Updated pricing: Check https://openai.com/pricing

**Data Available**:
- Daily token usage
- Cost breakdown by model
- Subscription status
- Hard limits

**Implementation Notes**:
- Usage data typically updates daily
- API is rate-limited; implement caching
- Consider storing daily snapshots instead of real-time queries

---

### 2. Anthropic (Claude)

**API Documentation**: https://docs.anthropic.com/claude/reference/getting-started-with-the-api

**Authentication**:
```
x-api-key: sk-ant-...
Content-Type: application/json
```

**Key Endpoints**:
- `GET /v1/messages` (with `usage` field in response)
- No dedicated usage/billing endpoint in current API
- Billing must be tracked via Anthropic Console or custom logging

**Rate Limits**: Depends on tier (standard, pro, enterprise)

**Cost Model**:
- Claude 3 Opus: ~$0.015/1K input tokens, $0.075/1K output tokens
- Claude 3 Sonnet: ~$0.003/1K input tokens, $0.015/1K output tokens
- Claude 3 Haiku: ~$0.00025/1K input tokens, $0.00125/1K output tokens
- Updated pricing: Check https://www.anthropic.com/pricing

**Data Available**:
- Input and output tokens per request (from response metadata)
- No aggregated usage endpoint
- Must implement custom logging

**Implementation Notes**:
- No native billing API; track usage in your app
- Each API response includes `usage.input_tokens` and `usage.output_tokens`
- Store these in database for historical tracking
- Consider webhooks for cost notifications from Anthropic

---

### 3. Groq

**API Documentation**: https://console.groq.com/docs/overview

**Authentication**:
```
Authorization: Bearer gsk_...
Content-Type: application/json
```

**Key Endpoints**:
- `POST /openai/v1/chat/completions` (usage in response)
- No dedicated usage/billing endpoint
- Dashboard available at https://console.groq.com

**Rate Limits**: Tier-dependent (free tier: moderate limits)

**Cost Model**:
- Groq Mixtral-8x7b: Free
- Groq Llama-2-70b: Free
- Additional models pricing varies
- Check https://groq.com for current pricing

**Data Available**:
- Tokens per request (from response metadata)
- No aggregated usage API
- Manual dashboard tracking or custom logging

**Implementation Notes**:
- Primarily free tier; track usage manually
- Each response includes `usage` field with token counts
- Store locally for tracking across sessions

---

### 4. Perplexity

**API Documentation**: Check https://docs.perplexity.ai or contact Perplexity

**Authentication**:
```
Authorization: Bearer pplx_...
Content-Type: application/json
```

**Key Endpoints**:
- `POST /chat/completions`
- Usage typically returned in response headers or body
- Check current API docs for billing endpoints

**Rate Limits**: Subscription-dependent

**Cost Model**:
- Free tier: Limited queries
- Pro tier: $20/month for unlimited
- Pricing details: https://www.perplexity.ai/pricing

**Data Available**:
- Queries used
- Subscription status
- Usage limits

**Implementation Notes**:
- API relatively new; documentation may be limited
- Recommend storing request/response logs for tracking
- Consider implementing query count in your app

---

### 5. GitHub Copilot

**API Documentation**: Limited; primarily VS Code Extension

**Authentication**:
- GitHub Personal Access Token (PAT) or
- GitHub App authentication

**Key Endpoints**:
- No direct usage API available for individual usage
- Organization-level usage: `GET /orgs/{org}/copilot/billing/seats` (requires admin)
- Check https://docs.github.com/en/rest/copilot for latest

**Rate Limits**: Standard GitHub API limits

**Cost Model**:
- Individual: $10/month or $100/year
- Business: $21/month per user
- Enterprise: Custom pricing

**Data Available**:
- Subscription status
- Seat count (organization level)
- Limited granular usage data

**Implementation Notes**:
- No real-time token usage tracking API
- Recommend manual entry or VS Code extension hook
- Consider tracking via logout/login timestamps
- GitHub Copilot Telemetry might expose some usage data

---

### 6. Additional Services (Codex, etc.)

**Codex** is now part of OpenAI's API, use OpenAI integration above.

---

## Request/Response Examples

### OpenAI Usage Query

**Request**:
```bash
curl -H "Authorization: Bearer sk-..." \
  "https://api.openai.com/v1/dashboard/billing/usage?start_date=2024-01-01&end_date=2024-01-31"
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "timestamp": 1704067200,
      "line_items": [
        {
          "name": "GPT-4 - 8K context",
          "cost": 5.25
        },
        {
          "name": "GPT-3.5 Turbo",
          "cost": 0.15
        }
      ]
    }
  ],
  "total_usage": 5.40
}
```

### Claude API Request with Usage

**Request**:
```bash
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: sk-ant-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello, Claude!"}
    ]
  }'
```

**Response**:
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [...],
  "model": "claude-3-sonnet-20240229",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 50
  }
}
```

---

## Implementation Priority

**Phase 1 (MVP)**:
1. OpenAI (most common, has billing API)
2. Manual tracking for others

**Phase 2**:
3. Anthropic Claude
4. Groq

**Phase 3**:
5. Perplexity
6. GitHub Copilot

**Phase 4+**:
7. Additional services as requested

---

## Storing API Keys Securely

**Backend Implementation**:

```python
from cryptography.fernet import Fernet
import os

# Load encryption key from environment
encryption_key = os.getenv('ENCRYPTION_KEY')
cipher = Fernet(encryption_key)

# Encrypting
api_key = "sk-..."
encrypted_key = cipher.encrypt(api_key.encode())

# Decrypting (only when needed for API calls)
decrypted_key = cipher.decrypt(encrypted_key).decode()
```

**Environment Setup**:
```bash
# Generate key once
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
ENCRYPTION_KEY=your_generated_key_here
```

---

## Error Handling Guidelines

For each service, handle:
- Invalid credentials (401 Unauthorized)
- Rate limit exceeded (429 Too Many Requests)
- Service unavailable (503 Service Unavailable)
- Network timeouts
- Malformed responses

Implement exponential backoff retry logic for transient failures.

---

## Testing with Mock Data

For development without using real API calls:

```python
# mock_services.py
MOCK_OPENAI_RESPONSE = {
    "total_usage": 15.50,
    "daily_usage": [
        {"date": "2024-02-20", "cost": 0.50},
        {"date": "2024-02-21", "cost": 0.75},
    ]
}

def get_openai_usage_mock():
    return MOCK_OPENAI_RESPONSE
```

Use dependency injection to switch between real and mock services during testing.
