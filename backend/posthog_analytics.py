"""PostHog LLM analytics integration for tracking LLM calls."""

import time
from typing import List, Dict, Any, Optional
from posthog import Posthog


class PostHogAnalytics:
    """Handles PostHog LLM analytics tracking."""

    def __init__(self, api_key: Optional[str], host: str = "https://us.i.posthog.com", enabled: bool = True):
        """
        Initialize PostHog analytics client.

        Args:
            api_key: PostHog API key from project settings
            host: PostHog host URL (defaults to US cloud)
            enabled: Whether analytics tracking is enabled
        """
        self.enabled = enabled and api_key is not None
        self.client = None

        if self.enabled:
            try:
                self.client = Posthog(
                    project_api_key=api_key,
                    host=host
                )
            except Exception as e:
                print(f"Failed to initialize PostHog client: {e}")
                self.enabled = False

    def track_generation(
        self,
        distinct_id: str,
        model: str,
        provider: str,
        input_messages: List[Dict[str, str]],
        output_content: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        latency: Optional[float] = None,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        span_id: Optional[str] = None,
        span_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        http_status: Optional[int] = None,
        is_error: bool = False,
        error: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track an LLM generation event.

        Args:
            distinct_id: Unique identifier for the user/conversation
            model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4.5")
            provider: Provider name (e.g., "openai", "anthropic", "google")
            input_messages: List of input messages sent to the LLM
            output_content: The generated output content
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency: Request latency in seconds
            trace_id: Trace ID for grouping related events
            session_id: Session ID for grouping related traces
            span_id: Unique span identifier
            span_name: Name for this generation
            parent_id: Parent span ID for hierarchical grouping
            http_status: HTTP status code
            is_error: Whether the request resulted in an error
            error: Error message if any
            temperature: Temperature parameter used
            max_tokens: Max tokens parameter used
            custom_properties: Additional custom properties
        """
        if not self.enabled or not self.client:
            return

        try:
            # Build properties according to PostHog $ai_generation schema
            properties = {
                "$ai_model": model,
                "$ai_provider": provider,
                "$ai_input": [{"role": msg["role"], "content": [{"type": "text", "text": msg["content"]}]}
                             for msg in input_messages],
                "$ai_output_choices": [{"role": "assistant", "content": [{"type": "text", "text": output_content}]}],
            }

            # Add optional token counts
            if input_tokens is not None:
                properties["$ai_input_tokens"] = input_tokens
            if output_tokens is not None:
                properties["$ai_output_tokens"] = output_tokens

            # Add latency
            if latency is not None:
                properties["$ai_latency"] = latency

            # Add trace/session/span info
            if trace_id:
                properties["$ai_trace_id"] = trace_id
            if session_id:
                properties["$ai_session_id"] = session_id
            if span_id:
                properties["$ai_span_id"] = span_id
            if span_name:
                properties["$ai_span_name"] = span_name
            if parent_id:
                properties["$ai_parent_id"] = parent_id

            # Add HTTP status and error info
            if http_status is not None:
                properties["$ai_http_status"] = http_status
            properties["$ai_is_error"] = is_error
            if error:
                properties["$ai_error"] = error

            # Add model parameters
            if temperature is not None:
                properties["$ai_temperature"] = temperature
            if max_tokens is not None:
                properties["$ai_max_tokens"] = max_tokens

            # Add base URL for OpenRouter
            properties["$ai_base_url"] = "https://openrouter.ai/api/v1"
            properties["$ai_request_url"] = "https://openrouter.ai/api/v1/chat/completions"

            # Add any custom properties
            if custom_properties:
                properties.update(custom_properties)

            # Capture the event
            self.client.capture(
                distinct_id=distinct_id,
                event="$ai_generation",
                properties=properties
            )

        except Exception as e:
            # Don't let analytics errors break the application
            print(f"Error tracking generation to PostHog: {e}")

    def track_span(
        self,
        distinct_id: str,
        span_name: str,
        input_state: Dict[str, Any],
        output_state: Dict[str, Any],
        trace_id: str,
        session_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        latency: Optional[float] = None,
        is_error: bool = False,
        error: Optional[str] = None
    ) -> None:
        """
        Track a custom span event (e.g., for tracking stages in the council process).

        Args:
            distinct_id: Unique identifier for the user/conversation
            span_name: Name of the span (e.g., "stage1_collect", "stage2_rank")
            input_state: Input state of the span
            output_state: Output state of the span
            trace_id: Trace ID for grouping
            session_id: Session ID for grouping traces
            span_id: Unique span identifier
            parent_id: Parent span ID
            latency: Span latency in seconds
            is_error: Whether the span had an error
            error: Error message if any
        """
        if not self.enabled or not self.client:
            return

        try:
            properties = {
                "$ai_trace_id": trace_id,
                "$ai_span_name": span_name,
                "$ai_input_state": input_state,
                "$ai_output_state": output_state,
                "$ai_is_error": is_error
            }

            if session_id:
                properties["$ai_session_id"] = session_id
            if span_id:
                properties["$ai_span_id"] = span_id
            if parent_id:
                properties["$ai_parent_id"] = parent_id
            if latency is not None:
                properties["$ai_latency"] = latency
            if error:
                properties["$ai_error"] = error

            self.client.capture(
                distinct_id=distinct_id,
                event="$ai_span",
                properties=properties
            )

        except Exception as e:
            print(f"Error tracking span to PostHog: {e}")

    def shutdown(self) -> None:
        """Shutdown the PostHog client and flush any pending events."""
        if self.client:
            try:
                self.client.shutdown()
            except Exception as e:
                print(f"Error shutting down PostHog client: {e}")


# Global analytics instance
_analytics_instance: Optional[PostHogAnalytics] = None


def initialize_analytics(api_key: Optional[str], host: str = "https://us.i.posthog.com", enabled: bool = True) -> PostHogAnalytics:
    """
    Initialize the global PostHog analytics instance.

    Args:
        api_key: PostHog API key
        host: PostHog host URL
        enabled: Whether to enable analytics

    Returns:
        PostHogAnalytics instance
    """
    global _analytics_instance
    _analytics_instance = PostHogAnalytics(api_key=api_key, host=host, enabled=enabled)
    return _analytics_instance


def get_analytics() -> Optional[PostHogAnalytics]:
    """Get the global PostHog analytics instance."""
    return _analytics_instance
