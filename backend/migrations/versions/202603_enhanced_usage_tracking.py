"""Enhanced usage tracking schema with provider-specific metrics

Revision ID: 202603_enhanced
Revises: (previous)
Create Date: 2026-03-02

Adds rich metrics for all 6 AI providers:
- Token breakdowns (input/output/cache)
- Rate limit tracking
- Service tiers (Anthropic)
- Performance metrics (Groq, Google)
- Provider-specific fields
""\