"""Calls the GitLab REST API through `glab api`, which carries the operator's authentication."""

import json
import subprocess

FIREWALL_STATUS_MARKER = "HTTP 403"
FIREWALL_PAGE_MARKER = "<!doctype html"
ERROR_EXCERPT_LENGTH = 500


class GitLabApiError(Exception):
    pass


class FirewallBlockedError(GitLabApiError):
    """The gateway in front of gitlab.syneto.eu rejected the request body as an attack.

    It answers with an HTML 403 page instead of a GitLab JSON error. Known trigger: the
    text `time (`, which it reads as SQL injection.
    """


def call_gitlab_api(hostname: str, endpoint: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    command = ["glab", "api", "--hostname", hostname, "--method", method, endpoint]
    request_body = None
    if payload:
        command += ["--header", "Content-Type: application/json", "--input", "-"]
        request_body = json.dumps(payload)

    completed = subprocess.run(command, input=request_body, capture_output=True, text=True)
    if completed.returncode:
        combined_output = f"{completed.stderr}\n{completed.stdout}"
        if FIREWALL_STATUS_MARKER in completed.stderr and FIREWALL_PAGE_MARKER in combined_output.lower():
            raise FirewallBlockedError(f"{method} {endpoint}")
        raise GitLabApiError(f"{method} {endpoint} failed: {combined_output.strip()[:ERROR_EXCERPT_LENGTH]}")
    return json.loads(completed.stdout) if completed.stdout.strip() else {}
