"""
Seed the services table with initial AI provider definitions.

Run from the backend directory with the venv activated:
    python scripts/seed_services.py
"""

import sys
import os

# Allow running from project root or backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models.service import Service

SERVICES = [
    {
        "name": "ChatGPT",
        "api_provider": "OpenAI",
        "has_api": True,
        "pricing_model": {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        },
    },
    {
        "name": "Claude",
        "api_provider": "Anthropic",
        "has_api": True,
        "pricing_model": {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        },
    },
    {
        "name": "Groq",
        "api_provider": "Groq",
        "has_api": True,
        "pricing_model": {
            "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
            "llama2-70b-4096": {"input": 0.0, "output": 0.0},
            "gemma-7b-it": {"input": 0.0, "output": 0.0},
        },
    },
    {
        "name": "GitHub Copilot",
        "api_provider": "GitHub",
        "has_api": False,
        "pricing_model": {
            "individual": {"subscription": 10.0},
            "business": {"subscription": 21.0},
        },
    },
    {
        "name": "Perplexity",
        "api_provider": "Perplexity",
        "has_api": True,
        "pricing_model": {
            "free": {"queries": 5, "cost": 0},
            "pro": {"cost": 20.0},
        },
    },
]


def seed():
    app = create_app()
    with app.app_context():
        for data in SERVICES:
            existing = Service.query.filter_by(name=data["name"]).first()
            if existing:
                print(f"  [skip] {data['name']} already exists.")
                continue
            service = Service(**data)
            db.session.add(service)
            print(f"  [add]  {data['name']}")
        db.session.commit()
        print("Done. Services seeded successfully.")


if __name__ == "__main__":
    seed()
