"""OpenRouter API client for making LLM requests."""

import httpx
import time
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL
from .posthog_analytics import get_analytics


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    span_name: Optional[str] = None,
    distinct_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        trace_id: Optional trace ID for PostHog analytics
        session_id: Optional session ID for PostHog analytics
        span_name: Optional span name for PostHog analytics
        distinct_id: Optional distinct ID for PostHog analytics

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    start_time = time.time()
    analytics = get_analytics()
    http_status = None
    is_error = False
    error_message = None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            http_status = response.status_code
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            latency = time.time() - start_time

            # Extract provider from model string (e.g., "openai/gpt-4o" -> "openai")
            provider = model.split('/')[0] if '/' in model else "unknown"

            # Track to PostHog if enabled
            if analytics and distinct_id:
                analytics.track_generation(
                    distinct_id=distinct_id,
                    model=model,
                    provider=provider,
                    input_messages=messages,
                    output_content=message.get('content', ''),
                    input_tokens=usage.get('prompt_tokens'),
                    output_tokens=usage.get('completion_tokens'),
                    latency=latency,
                    trace_id=trace_id,
                    session_id=session_id,
                    span_name=span_name,
                    http_status=http_status,
                    is_error=False
                )

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        latency = time.time() - start_time
        is_error = True
        error_message = str(e)

        print(f"Error querying model {model}: {e}")

        # Track error to PostHog if enabled
        if analytics and distinct_id:
            provider = model.split('/')[0] if '/' in model else "unknown"
            analytics.track_generation(
                distinct_id=distinct_id,
                model=model,
                provider=provider,
                input_messages=messages,
                output_content="",
                latency=latency,
                trace_id=trace_id,
                session_id=session_id,
                span_name=span_name,
                http_status=http_status,
                is_error=True,
                error=error_message
            )

        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    span_name_prefix: Optional[str] = None,
    distinct_id: Optional[str] = None
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        trace_id: Optional trace ID for PostHog analytics
        session_id: Optional session ID for PostHog analytics
        span_name_prefix: Optional prefix for span names (model name will be appended)
        distinct_id: Optional distinct ID for PostHog analytics

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [
        query_model(
            model,
            messages,
            trace_id=trace_id,
            session_id=session_id,
            span_name=f"{span_name_prefix}_{model}" if span_name_prefix else model,
            distinct_id=distinct_id
        )
        for model in models
    ]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
