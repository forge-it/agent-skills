---
name: cli-design
description: Command-line interface design guidelines for building human-friendly, robust, and composable CLI tools
license: MIT
metadata:
  author: cristian.ciortea@proton.me
  version: "0.0.1"
  based_on: "Command Line Interface Guidelines (https://clig.dev/)"
---

# CLI Design Skill

Version: 0.0.1

Based on: [Command Line Interface Guidelines](https://clig.dev/) — an open-source guide to help you write better command-line programs, taking traditional UNIX principles and updating them for the modern day.

## Purpose

This skill provides guidelines for designing and building command-line interfaces that are human-friendly, robust, composable, and future-proof. It covers arguments, flags, output, errors, help, configuration, and distribution.

## When to Apply

Apply these guidelines when:
- Designing a new CLI tool or application
- Adding subcommands, flags, or arguments to an existing CLI
- Implementing help text, error messages, or output formatting
- Reviewing CLI UX for consistency and usability

## Core Principles

### 1. Human-First Design (CRITICAL)

Design for humans first, machines second. The CLI is a text-based UI, not just a scripting interface. Prioritize usability, discoverability, and clear feedback.

### 2. Simple Parts That Work Together (CRITICAL)

Follow UNIX modularity — small programs with clean interfaces that compose into larger systems. Use plain line-based text for piping between commands. Use JSON when more structure is needed.

### 3. Consistency (HIGH)

Be consistent with widely-used conventions. Users have muscle memory for common patterns. Use the same flag names, output formats, and subcommand structures across your tool.

### 4. Say Just Enough (HIGH)

Balance information density. Too little output leaves users uncertain; too much overwhelms them. A command that hangs silently for minutes is saying too little. A command that dumps a wall of debug logs is saying too much.

## The Basics

### Exit Codes (CRITICAL)

- Return zero on success, non-zero on failure
- Use distinct non-zero codes for different failure modes when useful for scripting

### Output Streams (CRITICAL)

- Send primary output to stdout — this is the data users pipe to other commands
- Send all messaging (logs, errors, warnings, progress) to stderr
- This separation allows `myapp | jq` to work even when the app prints warnings

## Help

### Help Flags (CRITICAL)

Display help with `-h`, `--help`, and `myapp help`. When required arguments are missing, show concise usage rather than the full help text.

```
$ myapp --help
Usage: myapp <command> [options]

A tool for managing widgets.

Commands:
  create    Create a new widget
  list      List all widgets
  delete    Delete a widget

Options:
  -h, --help       Show this help message
  -v, --version    Show version
  --json           Output as JSON

Examples:
  myapp create --name "foo"
  myapp list --json | jq '.[0]'
  myapp delete --id 123 --force

Documentation: https://example.com/docs
Issues: https://github.com/example/myapp/issues
```

### Help Content (HIGH)

- Lead with examples showing common and complex uses
- Display the most common flags and commands first
- Provide a link to web documentation and issue tracker
- Suggest corrections when users mistype: "Did you mean 'list'?"

## Arguments and Flags

### Prefer Flags Over Positional Arguments (CRITICAL)

Flags are self-documenting and order-independent. Use positional arguments only for the most obvious, primary inputs.

```
# Good — clear what each value means
myapp create --name "foo" --type bar

# Acceptable — obvious primary argument
myapp open ./file.txt

# Bad — what does each positional arg mean?
myapp deploy production us-east-1 3
```

### Flag Conventions (CRITICAL)

- Always provide both short (`-h`) and long (`--help`) forms
- Reserve single-letter flags for the most common options
- Use standard flag names where conventions exist:
  - `-a/--all`, `-d/--debug`, `-f/--force`, `-n/--dry-run`
  - `-o/--output`, `-p/--port`, `-q/--quiet`, `-u/--user`
  - `-v/--version`, `-h/--help`, `--json`, `--no-input`

### Argument Parsing (HIGH)

Use an argument parsing library — never parse arguments manually. Examples: `clap` (Rust), `Click` (Python), `Cobra` (Go), `commander` (Node.js).

### Sensitive Input (CRITICAL)

- Never accept secrets via flags — they leak into shell history and process listings
- Use `--password-file`, stdin, or environment variables for secrets
- Prefer dedicated secret management over environment variables when possible

### Confirmation for Dangerous Actions (HIGH)

- Mild danger: allow `--force` to skip confirmation
- Moderate danger: require explicit confirmation prompt
- Severe danger: require typing a confirmation string (e.g., the resource name)

```
$ myapp delete --id production-db
This will permanently delete 'production-db'. Type the name to confirm:
```

## Output

### Human-Readable by Default (CRITICAL)

- Detect whether stdout is an interactive terminal (TTY)
- Format output for humans when interactive, for machines when piped
- Provide `--json` flag for structured machine-readable output
- Provide `--plain` flag for tabular output that disables formatting

### Success Feedback (CRITICAL)

Always confirm successful actions. Do not follow the UNIX silence convention — modern users expect feedback.

```
# Good
$ myapp deploy --env production
Deployed v2.3.1 to production (3 instances)

# Bad — what happened?
$ myapp deploy --env production
$
```

### State and Next Steps (HIGH)

- Tell users when state has changed and what changed
- Make current state easily visible (like `git status`)
- Suggest logical next commands to guide workflows

```
$ myapp init
Initialized project in ./myapp
Next steps:
  myapp config set --key api_key --value YOUR_KEY
  myapp deploy
```

### Color and Formatting (HIGH)

- Use color intentionally to highlight important information, not everything
- Disable color when: stdout isn't a TTY, `NO_COLOR` env var is set, `TERM=dumb`, or `--no-color` is passed
- Disable animations when stdout isn't interactive
- Use a pager (like `less`) for lengthy output on interactive terminals

## Errors

### Human-Friendly Errors (CRITICAL)

Catch errors and rewrite them for humans. Include what went wrong, why, and how to fix it.

```
# Good
Error: Can't write to config.yaml — permission denied.
Fix: Run 'chmod +w config.yaml' or use sudo.

# Bad
Error: EACCES: permission denied, open '/home/user/.config/myapp/config.yaml'
```

### Error Presentation (HIGH)

- Maintain signal-to-noise ratio — group similar errors, don't dump stack traces by default
- Use red sparingly and intentionally
- For unexpected errors, offer to generate a bug report with debug information
- Make bug reporting effortless with pre-populated issue URLs

## Interactivity

### Prompt Only When Interactive (CRITICAL)

- Only show interactive prompts when stdin is an interactive TTY
- Support `--no-input` flag to disable all prompts and fail with clear usage if input is required
- Hide password input (disable terminal echo)
- Always allow Ctrl-C to exit; document any non-obvious exit methods

### Always Allow Non-Interactive Use (CRITICAL)

Every interactive prompt must have a flag or argument equivalent so the tool works in scripts and CI.

```
# Interactive
$ myapp login
Username: _

# Non-interactive equivalent
$ myapp login --username admin --password-file ./pass.txt
```

## Subcommands

### Consistency Across Subcommands (HIGH)

- Use the same flag names and output formatting across all subcommands
- Prefer "noun verb" ordering for multi-level subcommands: `myapp container create`
- Avoid ambiguous naming — "update" vs "upgrade" confuses users

## Robustness

### Responsiveness (CRITICAL)

- Print something within 100ms — acknowledge the command was received
- Announce network requests before making them
- Show progress indicators (spinners, progress bars) for operations over 1 second

### Resilience (HIGH)

- Validate user input early and fail fast with clear errors
- Implement timeouts with sensible defaults for network operations
- Make operations recoverable — pressing up-arrow and re-running should resume or retry gracefully
- Design for crash-only operation when possible — avoid cleanup, defer to next run

### Parallel Operations (HIGH)

- Ensure output from parallel operations isn't interleaved confusingly
- Print full logs for any operation that fails within a parallel batch

## Signals

### Ctrl-C Handling (CRITICAL)

- Exit immediately on Ctrl-C (INT signal) — say something before cleanup if needed
- Use timeouts for cleanup so it can't hang indefinitely
- Allow a second Ctrl-C to skip cleanup; inform users: "Press Ctrl+C again to force quit"
- Design expecting that cleanup may not run — assume interrupted state exists

## Configuration

### Precedence Order (CRITICAL)

Apply configuration in this order (highest to lowest priority):
1. Command-line flags
2. Environment variables
3. Project-level config file
4. User-level config file (`~/.config/myapp/`)
5. System-level config file

### Config File Locations (HIGH)

- Follow the XDG Base Directory Specification for config file placement
- Use `~/.config/myapp/` for user config
- Ask for consent before modifying any external configuration files
- When appending to system files, use dated comments

### Environment Variables (HIGH)

- Use uppercase letters, numbers, and underscores only
- Respect standard variables: `NO_COLOR`, `FORCE_COLOR`, `DEBUG`, `EDITOR`, `HTTP_PROXY`, `PAGER`, `TMPDIR`, `HOME`
- Read from `.env` files for project-specific configuration
- Never store secrets in environment variables — they leak into logs and process listings

## Naming

### Tool Naming (HIGH)

- Use simple, memorable, lowercase words
- Use dashes only if necessary — `mytool` over `my-tool`
- Keep it short for daily typing
- Avoid generic names that conflict with system utilities

## Distribution

### Packaging (HIGH)

- Distribute as a single binary when possible
- If not a binary, use the platform's native package manager
- Make uninstallation easy and document it
- Don't scatter files across the filesystem during installation

## Analytics

### No Telemetry Without Consent (CRITICAL)

- Never phone home without explicit user consent
- If collecting analytics, clearly explain what data is collected, why, how it's anonymized, and retention period
- Prefer opt-in over opt-out
- Consider alternatives: instrument web docs, track downloads, talk directly to users

## Anti-Patterns to Avoid

1. **Silent success**: Not confirming that an action succeeded
2. **Cryptic errors**: Showing raw stack traces or error codes without explanation
3. **Manual argument parsing**: Not using a parsing library
4. **Secrets in flags**: Accepting passwords or tokens as command-line arguments
5. **Ignoring NO_COLOR**: Not respecting the `NO_COLOR` environment variable
6. **Prompting in pipes**: Showing interactive prompts when stdin is not a TTY
7. **Missing --json**: Not providing structured output for scripting
8. **Inconsistent subcommands**: Different flag names or output formats across subcommands
9. **Hanging without feedback**: Long operations with no progress indication
10. **Unrecoverable Ctrl-C**: Trapping SIGINT and ignoring it or hanging during cleanup
11. **Breaking changes**: Changing flag behavior or output format without deprecation warnings
12. **Catch-all subcommands**: Treating unknown subcommands as a default action, preventing future additions
13. **Phoning home**: Collecting telemetry without user consent

## Guidelines

### Output
- Return zero on success, non-zero on failure
- Send data to stdout, messaging to stderr
- Detect TTY and format accordingly — human-readable by default, machine-readable when piped
- Support `--json` and `--plain` output modes
- Always confirm successful state changes
- Suggest next steps when appropriate
- Respect `NO_COLOR`, `TERM=dumb`, and `--no-color`
- Use a pager for lengthy interactive output

### Input
- Use argument parsing libraries — never parse manually
- Prefer flags over positional arguments
- Provide both short and long flag forms
- Use standard flag names where conventions exist
- Never accept secrets via flags
- Support `--no-input` for scripting
- Confirm before dangerous actions with escalating severity

### Errors
- Rewrite errors for humans: what happened, why, and how to fix it
- Don't dump stack traces by default
- Make bug reporting effortless

### Robustness
- Print something within 100ms
- Show progress for long operations
- Validate input early, fail fast
- Handle Ctrl-C gracefully with cleanup timeouts
- Design for crash-only operation

### Configuration
- Apply precedence: flags > env vars > project config > user config > system config
- Follow XDG Base Directory Specification
- Respect standard environment variables
- Never store secrets in environment variables

### Distribution
- Distribute as a single binary when possible
- Make installation and uninstallation straightforward
- Never collect telemetry without consent
