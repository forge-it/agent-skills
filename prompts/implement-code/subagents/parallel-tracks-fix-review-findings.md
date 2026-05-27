Your task is to fix every unaddressed finding across one or more implementation review files <X>, by dispatching subagents per finding. Group findings by track. Each track runs as its own serial queue. When multiple tracks have work, the tracks run in parallel — they touch disjoint directories with disjoint test suites, so they do not interfere. The work must not contradict the original plan <Z>.

A "track" is one review file. Typical setup is one backend review file and one frontend review file:
- If only one review file is provided, only one track runs.
- If two review files are provided (backend + frontend), both tracks run in parallel.
- If three or more (e.g. backend + frontend + infra), all tracks run in parallel.

Each subagent receives, and nothing else:
1. The single finding text it must fix (verbatim).
2. The path of the review file the finding came from.
3. The original plan path <Z> for context.
4. The contents of the worker prompt <W>, passed verbatim.

No summary of prior conversation. No batching. No merging of findings. No hints about other findings or other tracks.

Rules:
- One subagent per finding. The subagent fixes exactly that finding and nothing else — no opportunistic refactors, no neighbouring cleanups, no fixing the next finding "while we're here".
- Within a track: serial. Dispatch one subagent, wait for it to return, verify, mark the finding fixed, then dispatch the next finding in that track.
- Across tracks: parallel. If two or more tracks each have an unfixed finding ready, dispatch their next subagents in the same message (multiple tool calls in one response). The tracks work on disjoint directories with disjoint test suites and do not interfere.
- The finding's domain is fixed by the review file it came from. A backend-review finding only touches the backend; a frontend-review finding only touches the frontend. Cross-cutting findings (rare) should be flagged to the operator rather than dispatched.
- After each subagent returns:
  1. Verify the relevant tests still pass. Backend track: backend test suite only. Frontend track: frontend test suite only. If tests fail, stop that track and surface the failure to the operator — do not dispatch the next finding in that track. Other tracks may continue.
  2. Re-read the finding and confirm the code change actually addresses it. If it does not, dispatch a follow-up subagent for the same finding with the new context (what the previous attempt got wrong). Do not mark it fixed.
  3. Mark the finding as fixed in its review file. Append `[FIXED]` to the finding's heading, or move the finding under a `## Resolved` section — whichever fits the file's existing structure. Edit the review file in place.
- Do not contradict the original plan <Z>. If a finding seems to conflict with the plan, stop that track and ask the operator before dispatching.
- Do not skip, reorder, or defer a finding without explicit operator permission. "Deferred" means the operator confirmed the finding will be handled later; mark it `[DEFERRED]` in the review file with the operator's reason.
- Pass the worker prompt verbatim. Do not paraphrase, condense, summarise, or "improve" it — its framing is load-bearing.
- Do not read, merge, edit, or rewrite findings across files beyond marking them fixed or deferred.
- If the worker prompt does not fit the project's stack (e.g. wrong language), stop and ask the operator before dispatching — do not silently swap it.

Loop until every finding in every review file is marked `[FIXED]` or `[DEFERRED]`. A track finishes when its last finding is marked; remaining tracks continue independently.

<X> = review file paths, one per line — each file is its own track (e.g. one backend review, one frontend review)
<Z> = original plan path
<W> = worker prompt path (e.g. /home/cristi/Projects/agent-skills/prompts/implement-code/stack-based/implement-rust-vue-task.md)
