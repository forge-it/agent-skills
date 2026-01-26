---
name: logging-best-practices
description: Logging best practices focused on wide events for powerful debugging and analytics
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
---

# Logging Best Practices Skill

Version: 0.0.1

## Purpose

This skill provides guidelines for implementing effective logging in applications. It focuses on **wide events** (also called canonical log lines) - a pattern where you emit a single, context-rich event per request per service, enabling powerful debugging and analytics.

## When to Apply

Apply these guidelines when:
- Writing or updating logging code
- Adding logger.info, print, println!, info!, console.log, developer.log or similar depending on the programming language
- Designing logging strategy for new services
- Setting up logging infrastructure

## Core Principles

### 1. Wide Events (CRITICAL)

Emit **one context-rich event per request per service**. Instead of scattering log lines throughout your handler, consolidate everything into a single structured event emitted at request completion.

```python
import time
from datetime import datetime, timezone

wide_event = {
    "method": "POST",
    "path": "/checkout",
    "request_id": request.state.request_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}

try:
    user = get_user(request.state.user_id)
    wide_event["user"] = {"id": user.id, "subscription": user.subscription}

    cart = get_cart(user.id)
    wide_event["cart"] = {"total_cents": cart.total, "item_count": len(cart.items)}

    wide_event["status_code"] = 200
    wide_event["outcome"] = "success"
    return {"success": True}
except Exception as e:
    wide_event["status_code"] = 500
    wide_event["outcome"] = "error"
    wide_event["error"] = {"message": str(e), "type": type(e).__name__}
    raise
finally:
    wide_event["duration_ms"] = (time.time() - start_time) * 1000
    logger.info(wide_event)
```

### 2. High Cardinality & Dimensionality (CRITICAL)

Include fields with high cardinality (user IDs, request IDs - millions of unique values) and high dimensionality (many fields per event). This enables querying by specific users and answering questions you haven't anticipated yet.

### 3. Business Context (CRITICAL)

Always include business context: user subscription tier, cart value, feature flags, account age. The goal is to know "a premium customer couldn't complete a $2,499 purchase" not just "checkout failed."

### 4. Environment Characteristics (CRITICAL)

Include environment and deployment info in every event: commit hash, service version, region, instance ID. This enables correlating issues with deployments and identifying region-specific problems.

### 5. Single Logger (HIGH)

Use one logger instance configured at startup and import it everywhere. This ensures consistent formatting and automatic environment context.

### 6. Middleware Pattern (HIGH)

Use middleware to handle wide event infrastructure (timing, status, environment, emission). Handlers should only add business context.

### 7. Structure & Consistency (HIGH)

- Use JSON format consistently
- Maintain consistent field names across services
- Simplify to two log levels: `info` and `error`
- Never log unstructured strings

## Anti-Patterns to Avoid

1. **Scattered logs**: Multiple logger.info calls per request
2. **Multiple loggers**: Different logger instances in different files
3. **Missing environment context**: No commit hash or deployment info
4. **Missing business context**: Logging technical details without user/business data
5. **Unstructured strings**: `print('something wrong happened')` instead of structured data
6. **Inconsistent schemas**: Different field names across services

## Guidelines

### Wide Events
- Emit one wide event per service hop
- Include all relevant context
- Connect events with request ID
- Emit at request completion in finally block

### Context
- Support high cardinality fields (user_id, request_id)
- Include high dimensionality (many fields)
- Always include business context
- Always include environment characteristics (commit_hash, version, region)

### Structure
- Use a single logger throughout the codebase
- Use middleware for consistent wide events 
- Use JSON format for formatting
- Use key-value for rendering
- Maintain consistent schema (use consistent field names across all services. If one service uses user_id and another uses userId, querying becomes painful.)
- Limit yourself to four log levels: debug, info, warning, error
- Never log unstructured strings (every log must be structured with queryable fields)

### Common Pitfalls
- Avoid multiple log lines per request. The only exception is temporary verbose logging during AI-assisted debugging sessions.
- Design for unknown unknowns
- Always propagate request IDs across services
