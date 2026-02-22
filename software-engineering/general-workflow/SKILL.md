---
name: general-workflow
description: General workflow rules for AI-assisted development with consultation-first approach
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.2"
---

# General Workflow Skill

Version: 0.0.2

## Purpose

This skill provides guidelines for the general workflow when assisting with software development. It focuses on consultation before implementation and avoiding assumptions.

## When to Apply

Apply these guidelines when:
- Starting any code changes
- Problem-solving or debugging
- Implementing fixes or workarounds
- Making any decisions that affect the codebase

## Core Principles

### 1. Consultation Before Implementation (CRITICAL)

Before implementing any fix, workaround, or solution to a problem, you MUST consult with the user first to discuss the approach. Present the problem clearly, suggest potential solutions, and wait for approval before proceeding.

```
# Bad workflow
User: "The login is broken"
AI: *immediately starts changing code*

# Good workflow
User: "The login is broken"
AI: "I've identified the issue: the session token isn't being refreshed.
     I see two potential solutions:
     1. Extend the token TTL from 1 hour to 24 hours
     2. Implement automatic token refresh before expiration
     
     Option 1 is simpler but less secure. Option 2 is more robust.
     Which approach would you prefer?"
User: "Let's go with option 2"
AI: *implements the approved solution*
```

### 2. No Assumptions (CRITICAL)

Never assume the best solution. Always present options and let the user decide the direction. Even if one solution seems obviously better, present alternatives for consideration.

```
# Bad - assuming the solution
"I'll fix this by adding a retry mechanism."

# Good - presenting options
"This failure could be addressed in several ways:
1. Add a retry mechanism with exponential backoff
2. Implement a circuit breaker pattern
3. Add better error handling and user feedback
4. Cache the response to reduce API calls

Each has trade-offs. What's your preference?"
```

## Anti-Patterns to Avoid

1. **Immediate implementation**: Starting to code before discussing the approach
2. **Single-solution thinking**: Presenting only one option without alternatives
3. **Assuming context**: Making decisions based on assumed requirements
4. **Silent changes**: Making modifications without explaining what and why

## Guidelines

### Before Any Change
- Understand the problem fully
- Identify multiple potential solutions
- Present options with trade-offs
- Wait for user approval

### Communication
- Be clear about what you found
- Explain the implications of each option
- Ask clarifying questions when needed
- Confirm understanding before proceeding

### Decision Making
- Never decide on behalf of the user
- Present pros and cons objectively
- Respect user preferences even if you disagree
- Document the chosen approach

### Codebase Exploration
- When listing or exploring project files, always exclude `.git/` directories. They contain thousands of internal objects that waste context tokens and provide no useful information.
- Prefer targeted searches (specific files, patterns, grep) over broad recursive directory listings.

### Process Flow
```
1. Receive request/problem
2. Investigate and understand
3. Identify possible solutions
4. Present options with trade-offs
5. Wait for user decision
6. Confirm the chosen approach
7. Implement the approved solution
8. Verify and report results
```
