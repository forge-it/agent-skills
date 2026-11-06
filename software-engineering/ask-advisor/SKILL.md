---
name: ask-advisor
description: "Use when the operator invokes /ask-advisor <session>, or tells this session to send its questions to a named advisor session instead of asking them. Never self-select it."
argument-hint: "<advisor session name>"
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.1.3"
---

# Ask the advisor

For the rest of this session, questions go through the advisor session named by the argument
instead of to the operator.

Run `ListAgents` first: it prints this session's own name and the running peers. Without an
argument, ask the operator once which of them is the advisor; if the named advisor is not
listed, tell the operator and ask them directly.

Every question you would otherwise put to the operator (with `AskUserQuestion` or in chat) goes
to the advisor over `SendMessage`. Each message gives this session's name as `ListAgents` prints
it, without any ` [ref]`, the ticket you are working on (key and title; without a ticket, the
repository and branch), the question, the options you see and your recommendation.

**Operator-level questions go on to the operator.** A question is operator-level when the
decision belongs to the operator, not the advisor: scope or requirements they have not settled,
an approval or gate that a skill or their instructions reserve for them, a trade-off that is
theirs. Tell the advisor in the message that it is operator-level: it must nag the operator with
the `nag` from `~/.bashrc` until they answer, then stop it and relay the answer here. In a
Claude Code shell that function is not loaded, so give the advisor the script's two commands,
filled in. `nag.py` accepts only lowercase letters, digits and dashes as the id: use this
session's name lowercased, each run of other characters turned into one `-`, none at either end
(`SYN-3392 licensing big` → `syn-3392-licensing-big`). Without a ticket, or when the session's
name already holds its key, leave `<ticket key>: ` out of the title.

```
~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py start <nag id> \
  --title "<this session's name>: <ticket key>: <the question in a few words>"
~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py stop <nag id>
```

Either way, end your turn and wait: the advisor's reply arrives as a cross-session message. Do
not go ahead on a guess or work around the question. If the operator answers here instead, tell
the advisor so it stops the nag.
