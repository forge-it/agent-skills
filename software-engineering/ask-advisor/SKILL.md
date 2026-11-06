---
name: ask-advisor
description: "Use when the operator invokes /ask-advisor <session>, or tells this session to send its questions to a named advisor session instead of asking them. Never self-select it."
argument-hint: "<advisor session name>"
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.1.0"
---

# Ask the advisor

For the rest of this session, questions go to the advisor session named by the argument, not to
the operator. Without an argument, ask the operator once which session is the advisor.

Run `ListAgents` first: it prints this session's own name and shows whether the advisor is
running. If the advisor is not listed, tell the operator and ask them directly.

Every question you would otherwise put to the operator (with `AskUserQuestion` or in chat) goes
to the advisor over `SendMessage`. Each message gives this session's name, so the advisor can
reply, the ticket you are working on (key and title; without a ticket, the repository and
branch), the question, the options you see and your recommendation.

**Operator-level questions block.** A question is operator-level when the decision belongs to
the operator, not the advisor: scope or requirements they have not settled, an approval or gate
that a skill or their instructions reserve for them, a trade-off that is theirs. For those:

1. Tell the advisor in the message that it is operator-level: it must nag the operator with
   `nag` from `~/.bashrc` until they answer, then stop the nag and relay the answer here. That
   function does not load in a Claude Code Bash shell, so give the advisor the script it runs:

   ```
   ~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py start <this session's name> \
     --title "<this session's name>: <the question in a few words>"
   ~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py stop <this session's name>
   ```

2. Stop and wait for the answer. Do not go ahead on a guess or work around the question.
