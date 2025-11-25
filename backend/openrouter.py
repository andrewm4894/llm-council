"""OpenRouter API client for making LLM requests with PostHog analytics."""

from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from .config import OPENROUTER_API_KEY, POSTHOG_API_KEY, POSTHOG_HOST

# Initialize OpenAI client configured for OpenRouter
# If PostHog is configured, use the wrapped client for automatic LLM analytics
if POSTHOG_API_KEY:
    from posthog import Posthog
    from posthog.ai.openai import AsyncOpenAI as PostHogAsyncOpenAI

    posthog_client = Posthog(POSTHOG_API_KEY, host=POSTHOG_HOST)
    openai_client = PostHogAsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        posthog_client=posthog_client,
    )
else:
    openai_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    posthog_distinct_id: Optional[str] = None,
    posthog_session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        posthog_distinct_id: Optional PostHog distinct ID to link LLM calls with users
        posthog_session_id: Optional PostHog session ID to link conversations together

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    try:
        # Build kwargs for the API call
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": timeout,
        }
        # Add PostHog tracking if configured
        if POSTHOG_API_KEY:
            if posthog_distinct_id:
                kwargs["posthog_distinct_id"] = posthog_distinct_id
            if posthog_session_id:
                kwargs["posthog_properties"] = {"$ai_session_id": posthog_session_id}

        response = await openai_client.chat.completions.create(**kwargs)

        message = response.choices[0].message

        return {
            'content': message.content,
            'reasoning_details': getattr(message, 'reasoning_details', None)
        }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    posthog_distinct_id: Optional[str] = None,
    posthog_session_id: Optional[str] = None
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        posthog_distinct_id: Optional PostHog distinct ID to link LLM calls with users
        posthog_session_id: Optional PostHog session ID to link conversations together

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages, posthog_distinct_id=posthog_distinct_id, posthog_session_id=posthog_session_id) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
