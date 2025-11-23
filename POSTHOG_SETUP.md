# PostHog LLM Analytics Setup

This document explains how to set up PostHog LLM analytics for the LLM Council project.

## Overview

PostHog LLM analytics has been integrated into this project to track:
- Individual LLM generation calls (all council models + chairman)
- Token usage (input/output tokens)
- Latency metrics for each LLM call
- Stage-level spans (Stage 1, Stage 2, Stage 3)
- Full council process traces
- Conversation-level tracking

## Configuration

All PostHog configuration is done via environment variables in your `.env` file:

### Environment Variables

```bash
# Enable/disable PostHog analytics
POSTHOG_ENABLED=true

# Your PostHog API key (get this from PostHog project settings)
POSTHOG_API_KEY=phc_your_api_key_here

# PostHog host (defaults to US cloud if not specified)
POSTHOG_HOST=https://us.i.posthog.com
```

**Note**: For EU cloud, use `https://eu.i.posthog.com`

### Getting Your PostHog API Key

1. Sign up for PostHog at https://posthog.com
2. Create a new project
3. Go to Project Settings → Project API Key
4. Copy the project API key (starts with `phc_`)

## Setup Steps

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your PostHog credentials to `.env`:
   ```bash
   POSTHOG_ENABLED=true
   POSTHOG_API_KEY=phc_your_actual_api_key
   POSTHOG_HOST=https://us.i.posthog.com
   ```

3. Restart the backend server:
   ```bash
   python -m backend.main
   ```

You should see a message: `PostHog LLM analytics initialized (host: https://us.i.posthog.com)`

## What Gets Tracked

### Generation Events (`$ai_generation`)

Every LLM call is tracked with:
- `$ai_model` - Model identifier (e.g., "openai/gpt-4o")
- `$ai_provider` - Provider name (e.g., "openai", "anthropic", "google")
- `$ai_input` - Input messages sent to the LLM
- `$ai_output_choices` - Generated output
- `$ai_input_tokens` - Number of input tokens
- `$ai_output_tokens` - Number of output tokens
- `$ai_latency` - Request latency in seconds
- `$ai_trace_id` - Conversation ID for grouping
- `$ai_span_name` - Stage identifier (e.g., "stage1_openai/gpt-4o")
- `$ai_http_status` - HTTP status code
- `$ai_is_error` - Whether the request failed

### Span Events (`$ai_span`)

Custom spans track each stage of the council process:
- `stage1_collect_responses` - Stage 1 collection
- `stage2_collect_rankings` - Stage 2 ranking
- `stage3_synthesize_final` - Stage 3 synthesis
- `full_council_process` - Overall process
- `generate_title` - Title generation

Each span includes:
- Input/output state
- Latency
- Success/error status
- Conversation ID for tracing

### Trace Grouping

All events for a single conversation are grouped by `$ai_trace_id` (the conversation UUID), allowing you to:
- See all LLM calls for a conversation
- Track total token usage per conversation
- Analyze latency across all stages
- Identify which models are used most frequently

## Viewing Analytics in PostHog

1. Go to your PostHog dashboard
2. Navigate to **LLM Analytics** section
3. View:
   - **Generations**: Individual LLM calls
   - **Traces**: Conversation-level aggregations
   - **Spans**: Stage-level operations

You can create custom dashboards to track:
- Token usage over time
- Average latency per model
- Error rates by provider
- Cost analysis (if you add pricing data)

## Disabling Analytics

To disable PostHog tracking:

1. Set `POSTHOG_ENABLED=false` in `.env`, OR
2. Remove/comment out the PostHog environment variables

The application will continue to work normally without analytics.

## Privacy Considerations

- **User Input**: User queries are sent to PostHog as part of the input data
- **Model Outputs**: LLM responses are sent to PostHog as part of the output data
- **Distinct ID**: Uses conversation UUID (not user-identifiable)

If you need to anonymize data further:
- Modify `backend/posthog_analytics.py` to filter sensitive content
- Use PostHog's privacy mode features
- Set up data retention policies in PostHog settings

## Performance Impact

PostHog analytics tracking:
- Runs asynchronously (non-blocking)
- Does not wait for PostHog API responses
- Fails gracefully if PostHog is unavailable
- Minimal performance overhead (<10ms per call)

## Troubleshooting

### "PostHog LLM analytics disabled" message

This means either:
- `POSTHOG_ENABLED=false` in your `.env`
- `POSTHOG_API_KEY` is not set or invalid
- PostHog initialization failed (check console for errors)

### Events not appearing in PostHog

Check:
1. API key is correct and starts with `phc_`
2. Host URL is correct for your region
3. Backend server was restarted after config changes
4. No firewall blocking PostHog's API endpoint
5. Allow 1-2 minutes for events to appear in PostHog UI

### Error messages in console

PostHog errors are logged but don't break the application. Common issues:
- Invalid API key: Check your `.env` file
- Network timeout: Check internet connection
- Rate limiting: PostHog has API rate limits on some plans

## Advanced Configuration

### Custom Properties

You can add custom properties to track additional metadata by modifying the `track_generation()` calls in `backend/openrouter.py`.

Example:
```python
analytics.track_generation(
    # ... existing params ...
    custom_properties={
        "user_tier": "premium",
        "feature_flag": "new_ui"
    }
)
```

### Session Tracking

Currently, session_id is optional and not set. To enable session tracking:
- Add session management to the frontend
- Pass session_id through the API
- Update council functions to use session_id

## Documentation Links

- PostHog LLM Analytics: https://posthog.com/docs/llm-analytics
- PostHog Python SDK: https://posthog.com/docs/libraries/python
- Event Schema: https://posthog.com/docs/llm-analytics/installation/manual-capture

## Support

For issues with:
- **PostHog setup**: https://posthog.com/docs or PostHog community Slack
- **Integration bugs**: Create an issue in this repository
