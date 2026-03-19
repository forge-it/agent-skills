---
name: rest-api-design
description: Defines REST API design conventions. Use it whenever designing, implementing, reviewing, or documenting REST API endpoints.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# REST API Design Skill

## Purpose

This skill codifies REST API conventions. It ensures every API endpoint across services follows a consistent, predictable design. Apply these rules when writing controllers, routes, request/response schemas, and API documentation.

## When to Apply

- Designing new API endpoints or services
- Reviewing or refactoring existing API routes
- Writing request/response payload schemas
- Implementing query parameters or filters
- Versioning an API
- Writing or updating API documentation

---

## Endpoint Design Process

Follow these steps **in order** when creating a new endpoint:

1. **Identify the resource** — what noun does this operate on? (e.g., `vms`, `snapshots`, `users`)
2. **Decide flat vs. sub-resource** — use the decision rules in [URL Paths](#1-url-paths-critical)
3. **Choose the HTTP method** — see [HTTP Methods & Status Codes](#3-http-methods--status-codes)
4. **Build the URL path** — see [URL Paths](#1-url-paths-critical)
5. **Define query parameters** (GET/DELETE only) — see [Query Parameters](#4-query-parameters)
6. **Define request body** (POST/PATCH only) — see [Request Payloads](#5-request-payloads)
7. **Define response body and status codes** — see [Response Bodies](#6-response-bodies)
8. **Verify against the checklist** — see [Pre-Commit Checklist](#pre-commit-checklist)

---

## Core Conventions

### 1. URL Paths (CRITICAL)

**Rules:**

- Paths identify **resource names only** — use nouns, never verbs.
- Paths are **lowercase kebab-case** (`words-separated-by-dashes`).
- All APIs live under: `https://<host>/api`
- Each service owns a top-level group: `/api/auth`, `/api/storage`, `/api/virtualization`
- Resources within a service are **flat** — no nesting resources under other resources.
- Use kebab-case to combine words: `vm-replicas`, not `vms/replicas`.

**Allowed nesting (only these two cases):**

| Nesting type | When to use | HTTP method | Example |
|---|---|---|---|
| **State sub-resource** | The nested path represents a property or state of the parent | Any | `GET /vms/<id>/power` |
| **Action sub-resource** | The nested path triggers an operation on the parent | `POST` only | `POST /vms/<id>/clone` |

State sub-resources may have their own nested sub-resources for further state breakdown (e.g., `/vms/<id>/power/history`). **No other nesting is allowed.**

**Action sub-resources** are named after the operation concept. Words like `clone`, `restart`, or `migrate` function as nouns here — naming the operation as a thing (a "clone operation", a "restart operation"), not as imperative verbs. Each action sub-resource has its **own strongly typed request/response schema**.

**How to decide: flat resource vs. sub-resource?**

Ask: *"Can this entity be identified and queried independently of a parent?"*

- **Yes** → make it a **flat top-level resource** (e.g., snapshots exist independently of volumes)
- **No, it describes state/property of a parent** → **state sub-resource** (e.g., power state only makes sense on a VM)
- **No, it's an operation on a parent** → **action sub-resource** (e.g., clone only applies to a specific VM)

```
# CORRECT — flat top-level resources
/api/storage/volumes
/api/storage/volumes/<id>
/api/storage/snapshots
/api/storage/snapshots/<id>

# CORRECT — action sub-resources (POST only)
POST /api/virtualization/vms/<id>/clone            →  {"snapshot_name": "..."}
POST /api/virtualization/vms/<id>/clone-convert    →  {}
POST /api/virtualization/vms/<id>/restart          →  {}

# CORRECT — state sub-resource with nested state
POST /api/virtualization/vms/<id>/power            →  {"state": "on"}
GET  /api/virtualization/vms/<id>/power/history

# CORRECT — state change via PATCH on a state sub-resource
PATCH /api/protection/vm-replicas/<id>/storage     →  {"pool_name": "flash"}
```

```
# WRONG — nesting resources under resources
/api/storage/volumes/<volId>/snapshots
/api/storage/volumes/<volId>/snapshots/<snapshotId>

# WRONG — slash as word separator (creates hierarchy instead of naming)
/api/protection/vms/replicas
/api/protection/jobs/categories-tree

# RIGHT — kebab-case flat resources
/api/protection/vm-replicas
/api/protection/jobs-categories-tree
```

```
# WRONG — verbs as path segments (not action sub-resources on a specific resource)
/api/virtualization/vms/clone
GET /api/protection/get-all-jobs

# WRONG — action discriminator field (polymorphic endpoint, breaks strong typing)
POST /api/virtualization/vms  →  {"action": "clone", "snapshot_name": "..."}

# RIGHT — dedicated action sub-resources with their own schemas
POST /api/virtualization/vms/<id>/clone            →  {"snapshot_name": "..."}
POST /api/virtualization/vms/<id>/clone-convert    →  {}
```

### 2. Field Naming (CRITICAL)

- All field keys in request payloads and response bodies: **snake_case**.
- This applies at **all nesting levels**, including deeply nested objects.
- Field keys must be **static identifiers**, never dynamic.

```json
// WRONG — camelCase
{"userName": "alice", "lastLogin": "2025-01-01"}

// WRONG — dynamic keys (schema can't describe the shape)
{"policy_counts": {"gold": 4, "silver": 3}}

// RIGHT — snake_case with static keys
{"user_name": "alice", "last_login": "2025-01-01"}

// RIGHT — array of typed objects replaces dynamic keys
{"policy_counts": [{"name": "gold", "count": 4}, {"name": "silver", "count": 3}]}
```

### 3. HTTP Methods & Status Codes

**Allowed methods:**

| Method   | Purpose                                          | Request body | Response body |
|----------|--------------------------------------------------|--------------|---------------|
| `GET`    | Read / list resources                            | Never        | Yes           |
| `POST`   | Create a resource OR trigger an action           | Yes          | Yes           |
| `PATCH`  | Partially update an identified resource          | Yes          | Yes           |
| `DELETE` | Remove an identified resource                    | Never        | No            |

- `PUT` is **not used**. Always use `PATCH` for updates.
- `PATCH` targets a resource via URL path (`/resource/<id>`). The resource ID **must not** appear in the request body.
- `GET` and `DELETE` **never** have request bodies.

**Status codes — use exactly these:**

| Scenario | Status code | Response body |
|---|---|---|
| Successful read (single resource or list) | `200` | The resource or list |
| Successful resource creation | `201` | The created resource |
| Successful action (synchronous) | `200` | The action result |
| Successful action (asynchronous/job-based) | `202` | Job reference |
| Successful PATCH | `200` | The updated resource |
| Successful DELETE | `204` | **No body** |
| Request body validation failed | `422` | Error object |
| Malformed request syntax | `400` | Error object |
| Not authenticated | `401` | Error object |
| Authenticated but not authorized | `403` | Error object |
| Resource not found | `404` | Error object |
| Conflict (duplicate, state violation) | `409` | Error object |
| Server error | `500` | Error object |

### 4. Query Parameters

- Query parameter names: **camelCase** (this intentionally differs from snake_case body fields).
- Query parameters on `GET` requests act as **filters** on the result set.
- `DELETE` may use query parameters for modifiers (e.g., `?force=true`).
- `POST` and `PATCH` **never** use query parameters — all input goes in the request body.

**Standard query parameters for list endpoints:**

| Parameter | Purpose | Example |
|---|---|---|
| `page` | Page number (1-indexed) | `?page=2` |
| `pageSize` | Items per page (default: 50, max: 200) | `?pageSize=20` |
| `sort` | Field to sort by; prefix `-` for descending | `?sort=-created_at` |
| `fields` | Comma-separated fields to include | `?fields=id,name,status` |
| `exclude` | Comma-separated fields to exclude | `?exclude=metadata` |

All list endpoints **must** support `page` and `pageSize`. Other parameters are recommended.

```
# WRONG — encoding a filter in the path
GET /api/protection/jobs/count-ongoing

# RIGHT — filter as query parameter
GET /api/protection/jobs/count?status=ongoing
```

### 5. Request Payloads

- Request bodies are JSON.
- All field names: **snake_case**.
- Payloads are **strongly typed**: a given endpoint always accepts the same JSON shape.
- Each endpoint and each action sub-resource has its **own dedicated schema** — never multiplex operations through one endpoint using a discriminator field.

```json
// WRONG — polymorphic endpoint with action discriminator
POST /api/virtualization/vms  →  {"action": "create", "name": "my-vm", "cpu": 4}
POST /api/virtualization/vms  →  {"action": "clone", "source_id": "vm-123"}

// RIGHT — separate endpoints with dedicated schemas
POST /api/virtualization/vms              →  {"name": "my-vm", "cpu": 4}
POST /api/virtualization/vms/<id>/clone   →  {"snapshot_name": "before-clone"}
```

### 6. Response Bodies

**Success responses — single resource** (e.g., `GET /api/storage/volumes/<id>`):

```json
{
  "id": "vol-abc",
  "name": "data-volume",
  "size_gb": 100,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Success responses — list** (e.g., `GET /api/storage/volumes`):

```json
{
  "items": [...],
  "pagination": {
    "page": 2,
    "page_size": 20,
    "total_items": 142,
    "total_pages": 8
  }
}
```

All list endpoints **must** wrap results in `items` and include `pagination` metadata.

**Empty results:**

- An empty list returns `200` with `{"items": [], "pagination": {...}}`.
- `DELETE` returns `204` with **no response body** (HTTP 204 means "No Content").

**Error responses** — use this exact structure for all error status codes (4xx, 5xx):

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Volume with id 'vol-xyz' not found.",
    "details": {}
  }
}
```

- `code`: machine-readable **UPPER_SNAKE_CASE** identifier.
- `message`: human-readable explanation.
- `details`: object with additional context. Use `{}` when empty.

**Validation error example** (`422`):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "field_errors": [
        {"field": "name", "message": "must be between 1 and 255 characters"},
        {"field": "size_gb", "message": "must be a positive integer"}
      ]
    }
  }
}
```

### 7. Actions, Jobs & Tasks

Mutating operations (`POST`, `PATCH`, `DELETE`) **should** produce a job when the service uses an asynchronous or event-driven architecture. To determine whether to produce jobs:

- **Does the service already have a job/task system?** → All mutations in that service must produce jobs.
- **Is the operation long-running (could exceed 1s)?** → Must be async with a job.
- **Is the service fully synchronous with no job system?** → Jobs are not required.

When jobs are used:

- Return `202 Accepted` with the job reference:

```json
{
  "job_id": "job-456",
  "status": "pending",
  "result_url": "/api/protection/jobs/job-456"
}
```

- When the job completes successfully, its `result` field must contain the created or modified entity.

### 8. Versioning

- Each service is versioned independently (e.g., Protection API v2, Virtualization API v4).
- **No version bump** for backwards-compatible changes: adding new routes, adding new optional fields to responses.
- **Version bump required** for backwards-incompatible changes: removing or renaming routes, removing or renaming fields, changing field types, changing required fields.
- Endpoints scheduled for removal must be **deprecated first**, then removed in a later version.

### 9. Performance

- `GET` responses must return in **under 1 second**.
- All list endpoints must support **pagination** (see [Query Parameters](#4-query-parameters)).
- Provide `fields` and `exclude` query parameters to limit response payload size.
- If using data caching at service startup, invalidate caches using **both** strategies:
  1. A periodic background process that detects and refreshes stale data.
  2. Cache invalidation on every `POST`, `PATCH`, or `DELETE`.

---

## Pre-Commit Checklist

Before finalizing any endpoint, verify **every** item:

- [ ] URL path uses **nouns only** and is **lowercase kebab-case**
- [ ] Resource is **flat** within its service group (not nested under another resource)
- [ ] If sub-resource: it is a **state** sub-resource or an **action** sub-resource (nothing else)
- [ ] Action sub-resources use **POST** only
- [ ] HTTP method matches the operation (GET=read, POST=create/action, PATCH=update, DELETE=remove)
- [ ] Status code matches the scenario per the status codes table
- [ ] Request body field names are **snake_case**
- [ ] Response body field names are **snake_case**
- [ ] Query parameter names are **camelCase**
- [ ] No query parameters on POST or PATCH
- [ ] No request body on GET or DELETE
- [ ] Resource ID is in the URL path, **not** in the PATCH request body
- [ ] List endpoints return `{"items": [...], "pagination": {...}}` and support `page`/`pageSize`
- [ ] All JSON keys are **static** (no dynamic keys)
- [ ] Error responses use the standard `{"error": {"code", "message", "details"}}` structure
- [ ] Endpoint is **fully documented** — all fields, types, and structures

---

## Anti-Patterns

| # | Anti-Pattern | Why it's wrong | Correct approach |
|---|---|---|---|
| 1 | Verbs in URL paths | URLs identify resources, not actions | Model actions as sub-resources: `POST /vms/<id>/clone` |
| 2 | Nested resource hierarchies | Creates coupling and complex URLs | Keep resources flat: `/api/storage/snapshots/<id>` |
| 3 | Slash as word separator | Slashes create hierarchy, not word boundaries | Use kebab-case: `vm-replicas`, not `vms/replicas` |
| 4 | Dynamic keys in JSON | Breaks schema validation and code generation | Use arrays of typed objects with static keys |
| 5 | Resource ID in PATCH body | ID belongs in URL; body has only changed fields | `PATCH /resource/<id>` with body containing only updates |
| 6 | Query args on POST/PATCH | Mutation parameters belong in the request body | Move to request body |
| 7 | Undocumented endpoints | Consumers can't use what they can't discover | Document every endpoint, field, and type |
| 8 | Skipping jobs for mutations | Inconsistent async behavior | All mutations produce jobs when the service uses a job system |
| 9 | Action discriminator field | Polymorphic endpoints break strong typing | Use dedicated action sub-resources with their own schemas |
| 10 | `PUT` for updates | Full replacement is error-prone and rarely intended | Use `PATCH` for partial updates |
| 11 | Returning 204 with a body | 204 means "No Content" — body must be empty | Return 200 with data, or 204 with no body |
| 12 | Inconsistent error format | Consumers can't reliably parse errors | Use the standard `{"error": {...}}` structure |
| 13 | Bare arrays in list responses | Can't add pagination metadata later | Wrap in `{"items": [...], "pagination": {...}}` |

---

## Quick Reference — Valid URL Patterns

```
/api/auth/users
/api/auth/users/<id>

/api/virtualization/vms
/api/virtualization/vms/<id>
/api/virtualization/vms/<id>/power           # state sub-resource
/api/virtualization/vms/<id>/power/history   # nested under state (allowed)
/api/virtualization/vms/<id>/clone           # action sub-resource (POST only)
/api/virtualization/vms/<id>/clone-convert   # action sub-resource (POST only)
/api/virtualization/vms/<id>/restart         # action sub-resource (POST only)

/api/storage/volumes
/api/storage/volumes/<id>
/api/storage/volumes/<id>/meta               # state sub-resource
/api/storage/volumes?originalSnapshot=<snapshot>&page=1&pageSize=20

/api/storage/snapshots
/api/storage/snapshots/<id>

/api/protection/jobs
/api/protection/jobs/<id>
/api/protection/jobs/count?status=ongoing
```
