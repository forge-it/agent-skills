---
name: rest-api-design
description: Defines Syneto's REST API design conventions. Use it whenever designing, implementing, reviewing, or documenting REST API endpoints for Syneto OS services.
license: UNLICENSED
metadata:
  author: Syneto
  version: "0.0.1"
  source: "RFD0003"
---

# REST API Design Skill

## Purpose

This skill codifies the REST API conventions from RFD0003. It ensures every API endpoint across Syneto OS services follows a consistent, predictable design. Apply these rules when writing controllers, routes, request/response schemas, and API documentation.

## When to Apply

- Designing new API endpoints or services
- Reviewing or refactoring existing API routes
- Writing request/response payload schemas
- Implementing query parameters or filters
- Versioning an API service
- Writing or updating API documentation

---

## Endpoint Design Process

Follow these steps **in order** when creating a new endpoint:

1. **Identify the resource** — what noun does this operate on? (e.g., `vms`, `snapshots`, `users`)
2. **Decide flat vs. sub-resource** — use the decision rules in [URL Paths](#1-url-paths-critical)
3. **Choose the HTTP method** — see [HTTP Methods & Status Codes](#3-http-methods--status-codes)
4. **Build the URL path** — see [URL Paths](#1-url-paths-critical)
5. **Define query parameters** (GET/DELETE only) — see [Query Parameters](#4-query-parameters)
6. **Define request body** (POST/PATCH only) — see [Request Payloads & Response Bodies](#5-request-payloads--response-bodies)
7. **Define response body and status codes** — see [Response Bodies](#6-response-bodies)
8. **Verify against the checklist** — see [Pre-Commit Checklist](#pre-commit-checklist)

---

## Core Conventions

### 1. URL Paths (CRITICAL)

**Rules:**

- Paths identify **resource names only** — use nouns, never verbs.
- Paths are **lowercase kebab-case** (`words-separated-by-dashes`).
- All APIs live under the base URL: `https://<host>/api`
- Each service owns a top-level group: `/api/auth`, `/api/storage`, `/api/virtualization`, etc.
- **No nested resource hierarchies** within a service. All resources are top-level inside their service group.
- A resource may have nested sub-collections **only for its own state** (e.g. `/vms/<id>/power`).

**How to decide: flat resource vs. state sub-resource?**

Ask: *"Can this entity be identified and queried independently of a parent?"*

- **Yes** → make it a **flat top-level resource** (e.g., snapshots exist independently of volumes)
- **No, it describes state/property of a parent** → **state sub-resource** (e.g., power state only makes sense on a VM)

```
# WRONG — nested resources
/api/storage/volumes/<volId>/snapshots
/api/storage/volumes/<volId>/snapshots/<snapshotId>

# RIGHT — flat top-level resources
/api/storage/volumes
/api/storage/volumes/<id>
/api/storage/snapshots
/api/storage/snapshots/<id>
```

```
# WRONG — verbs in path
/api/virtualization/vms/clone
/api/protection/vms/replicas/<id>/move-storage

# RIGHT — use POST with action in payload
POST /api/virtualization/vms  →  {"action": "clone", "snapshotName": "..."}
PATCH /api/virtualization/vms/<id>  →  {"action": "clone-convert"}
PATCH /api/protection/vm-replicas/<id>/storage  →  {"poolName": "flash"}
```

```
# WRONG — slash as separator within a group
/api/protection/vms/replicas
/api/protection/jobs/categories-tree

# RIGHT — kebab-case flat resources
/api/protection/vm-replicas
/api/protection/jobs-categories-tree
```

### 2. Field Naming (CRITICAL)

- All field keys in request payloads and response bodies must be **camelCase**, including nested JSON keys.
- Field keys must be **static identifiers**, never dynamic.

```json
// WRONG — dynamic keys
{"policyCounts": {"gold": 4, "silver": 3}}

// RIGHT — static keys with array of typed objects
{"policyCounts": [{"name": "gold", "count": 4}, {"name": "silver", "count": 3}]}
```

### 3. HTTP Methods & Status Codes

**Allowed methods:**

| Method   | Purpose                                          | Request body | Response body |
|----------|--------------------------------------------------|--------------|---------------|
| `GET`    | Read / list resources                            | Never        | Yes           |
| `POST`   | Create a resource or trigger an action           | Yes          | Yes           |
| `PATCH`  | Partially update an identified resource          | Yes          | Yes           |
| `DELETE` | Remove an identified resource                    | Never        | No            |

- `PUT` is **not used**. Always use `PATCH` for updates.
- `PATCH` targets an identified resource via the URL path (`/resource/<id>`). The resource ID **must not** appear in the request body.
- `GET` and `DELETE` must **never** have request bodies.

**Status codes — use exactly these:**

| Scenario | Status code | Response body |
|---|---|---|
| Successful read (single resource or list) | `200` | The resource or list |
| Successful mutation (job created) | `202` | Job reference |
| Empty response | `204` | `[]` or `{}` |
| Malformed request syntax | `400` | Error object |
| Not authenticated | `401` | Error object |
| Authenticated but not authorized | `403` | Error object |
| Resource not found | `404` | Error object |
| Conflict (duplicate, state violation) | `409` | Error object |
| Request body validation failed | `422` | Error object |
| Server error | `500` | Error object |

### 4. Query Parameters

- Query parameter names follow **camelCase**.
- Query parameters on `GET` requests act as **filters** on the result set.
- `DELETE` may use query parameters for modifiers (e.g., `?force=true`).
- `POST` and `PATCH` must **never** use query parameters — all input goes in the request body.

**Standard query parameters for list endpoints:**

| Parameter | Purpose | Example |
|---|---|---|
| `page` | Page number (1-indexed) | `?page=2` |
| `pageSize` | Items per page | `?pageSize=20` |
| `sort` | Field to sort by; prefix `-` for descending | `?sort=-createdAt` |
| `fields` | Comma-separated fields to include | `?fields=id,name,status` |
| `exclude` | Comma-separated fields to exclude | `?exclude=metadata` |

```
# WRONG — encoding a filter in the path
GET /api/protection/jobs/count-ongoing

# RIGHT — filter as query parameter
GET /api/protection/jobs/count?status=ongoing
```

### 5. Request Payloads & Response Bodies

**Request payloads:**

- Payloads are JSON with **camelCase** field names.
- Payloads are **strongly typed**: the same shape of JSON is always accepted and returned for a given endpoint.

**Success responses — single resource** (e.g., `GET /api/storage/volumes/<id>`):

```json
{
  "id": "vol-abc",
  "name": "data-volume",
  "sizeGb": 100,
  "createdAt": "2025-01-15T10:30:00Z"
}
```

**Success responses — list** (e.g., `GET /api/storage/volumes`):

```json
{
  "items": [...],
  "pagination": {
    "page": 2,
    "pageSize": 20,
    "totalItems": 142,
    "totalPages": 8
  }
}
```

All list endpoints **must** wrap results in `items` and include `pagination` metadata.

**Empty responses** must return HTTP **204** with either `[]` or `{}` as the body.

**Error responses** — use this structure for all error status codes (4xx, 5xx):

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
      "fieldErrors": [
        {"field": "name", "message": "must be between 1 and 255 characters"},
        {"field": "sizeGb", "message": "must be a positive integer"}
      ]
    }
  }
}
```

### 6. Actions, Jobs & Tasks

- **Every** mutating action (`POST`, `PATCH`, `DELETE`) must produce a job, even for non-long-running operations.
- Return `202 Accepted` with the job reference:

```json
{
  "jobId": "job-456",
  "status": "pending",
  "resultUrl": "/api/protection/jobs/job-456"
}
```

- When the job completes successfully, its response body must include a `result` field containing the created or modified entity.

### 7. Versioning

- Each service is **versioned independently** (e.g. Protection API v2, Virtualization API v4).
- **No version bump needed** when only adding new routes or new optional fields (backwards-compatible changes).
- **Version bump required** when a route, query parameters, payload structure, or response body changes in a backwards-incompatible way (removing or renaming routes/fields, changing field types, changing required fields).
- Endpoints scheduled for removal must be **marked deprecated first**, then removed in a later version.

### 8. Performance

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
- [ ] Sub-resources are used **only for state** of a parent resource
- [ ] HTTP method matches the operation (GET=read, POST=create/action, PATCH=update, DELETE=remove)
- [ ] Status code matches the scenario per the status codes table
- [ ] All field names in request and response bodies are **camelCase**
- [ ] Query parameter names are **camelCase**
- [ ] No query parameters on POST or PATCH
- [ ] No request body on GET or DELETE
- [ ] Resource ID is in the URL path, **not** in the PATCH request body
- [ ] List endpoints return `{"items": [...], "pagination": {...}}` and support pagination
- [ ] All JSON keys are **static** (no dynamic keys)
- [ ] Error responses use the standard `{"error": {"code", "message", "details"}}` structure
- [ ] Every mutating operation produces a job
- [ ] Endpoint is **fully documented** — all fields, types, and structures

---

## Anti-Patterns

| # | Anti-Pattern | Why it's wrong | Correct approach |
|---|---|---|---|
| 1 | Verbs in URL paths | URLs identify resources, not actions | Use nouns only; encode actions in the request payload |
| 2 | Nested resource hierarchies | Creates coupling and complex URLs | Keep resources flat: `/api/storage/snapshots/<id>` |
| 3 | Slash as word separator | Slashes create hierarchy, not word boundaries | Use kebab-case: `vm-replicas`, not `vms/replicas` |
| 4 | Dynamic keys in JSON | Breaks schema validation and code generation | Use arrays of typed objects with static keys |
| 5 | Resource ID in PATCH body | ID belongs in URL; body has only changed fields | `PATCH /resource/<id>` with body containing only updates |
| 6 | Query args on POST/PATCH | Mutation parameters belong in the request body | Move to request body |
| 7 | Undocumented endpoints | Consumers can't use what they can't discover | Document every endpoint, field, and type |
| 8 | Skipping jobs for mutations | Inconsistent async behavior | All POST/PATCH/DELETE must produce a job |
| 9 | `PUT` for updates | Full replacement is error-prone and rarely intended | Use `PATCH` for partial updates |
| 10 | Inconsistent error format | Consumers can't reliably parse errors | Use the standard `{"error": {...}}` structure |
| 11 | Bare arrays in list responses | Can't add pagination metadata later | Wrap in `{"items": [...], "pagination": {...}}` |

---

## Quick Reference — Valid URL Patterns

```
/api/auth/users
/api/auth/users/<id>

/api/virtualization/vms
/api/virtualization/vms/<id>
/api/virtualization/vms/<id>/power          # state sub-resource

/api/storage/volumes
/api/storage/volumes/<id>
/api/storage/volumes/<id>/meta              # state sub-resource
/api/storage/volumes?originalSnapshot=<snapshot>&page=1&pageSize=20

/api/storage/snapshots
/api/storage/snapshots/<id>

/api/protection/jobs
/api/protection/jobs/<id>
/api/protection/jobs/count?status=ongoing
```

## Documentation Requirement

All API endpoints must be documented. Field names, types, and structures in both request payloads and response bodies must be **completely documented** — no undocumented fields.
