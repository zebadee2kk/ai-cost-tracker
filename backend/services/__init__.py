"""Service client registry.

Maps service names (as stored in the database) to their client class.
Add new service integrations here once implemented.
"""

from services.openai_service import OpenAIService
from services.anthropic_service import AnthropicService

# Mapping from Service.name (case-sensitive, as seeded) to client class.
# Services without an API integration (Groq, Perplexity) are omitted;
# they use the manual entry workflow instead.
SERVICE_CLIENTS = {
    "ChatGPT": OpenAIService,
    "OpenAI": OpenAIService,
    "Anthropic": AnthropicService,
    "Claude": AnthropicService,
}


def get_service_client(service_name: str, api_key: str):
    """Return an instantiated service client for the given service name.

    Raises ValueError if no client is registered for the service.
    """
    client_class = SERVICE_CLIENTS.get(service_name)
    if not client_class:
        raise ValueError(
            f"No API client registered for service '{service_name}'. "
            "This service may require manual entry."
        )
    return client_class(api_key)
