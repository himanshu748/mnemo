# Demo video script — target 2:55 (hard limit 3:00)

**Setup before recording:** clean sandbox workspace, Mnemo installed and green; one public channel `#project-atlas` with mnemo invited; Assistant pane empty (fresh user or after wiping the data dir); Claude Desktop or Claude Code open in a second window with Mnemo NOT yet added as an MCP server; screen recorder at 1080p; mic ready. Kill notifications (macOS Focus mode).

**Rule from Devpost:** no copyrighted music, video must show the real project functioning.

---

### 0:00–0:15 — Hook (Assistant pane visible, empty)

> "Every Slack bot has amnesia. Tell it your deadline today — tomorrow it's a stranger. This is Mnemo: a Slack teammate with an actual memory lifecycle — and memory that follows you off Slack too. Watch."

### 0:15–0:50 — Teach it, then test it (Assistant pane)

Type, one after another:

1. `Remember that our API gateway migration ships July 22, and staging freezes 3 days before.`
2. `I prefer answers as short bullet points.`
3. Then ask a **paraphrase**, not the same words: `When do we need to stop merging to staging?`

> "I never said 'stop merging' — Mnemo recalled the freeze rule and did the date math. Look at the footer: it answered from 2 memories, ~40 context tokens — not my whole chat history. That accounting is in every reply."

*(Zoom/point at the footer: "recalled N memories · N context tokens · % smaller".)*

### 0:50–1:10 — Explicit controls

- `/remember The client demo login is demo@acme.test` → show the confirmation.
- `/recall demo` → show it surfaces the right fact.

> "Slash commands give direct control — and any message can become memory too, via the 'Remember this' shortcut in the ⋯ menu."

### 1:10–1:50 — The differentiator: /sleep (consolidate AND flag conflicts, one pass)

In `#project-atlas`, seed four facts quickly:

1. `/remember Standup is at 9am.`
2. `/remember Standup is at 9:30am.`
3. `/remember Ravi runs standup on Fridays.`
4. `/remember Ravi is the one running our Friday standups.`

Then: `/sleep`

> "Watch what one sleep pass does. Facts 3 and 4 agree — Mnemo merges them into one durable fact and lets the raw duplicates fade. But facts 1 and 2 *disagree* — different times for the same thing — so instead of silently picking one, it flags the conflict right back to the channel and asks the team to resolve it. That's the difference between storage and judgment."

*(Show the response: consolidated fact, pruned count, and the ⚠️ conflict message posted in-channel.)*

### 1:50–2:05 — Shared channel memory

`@mnemo what do you know about this project?`

> "Channels get shared team memory, separate from everyone's private memory — what the team teaches Mnemo here, the whole team can recall here."

### 2:05–2:45 — The same memory, outside Slack (MCP)

- `/mnemo-token` → show the token response in Slack.
- Cut to Claude Desktop/Code: add Mnemo as an MCP server at the given URL, paste the token into the first message.
- Ask it: `What does Mnemo remember about my staging freeze?`

> "Mnemo also runs as an MCP server. That token I just minted in Slack connects Claude Desktop to my *exact* Slack memory — not a copy. Ask it anything I taught Mnemo in Slack, and it just knows — because it's reading and writing the same store."

### 2:45–2:55 — Close (architecture diagram on screen)

> "Bolt for Python on Slack's Assistant APIs, an MCP server for every other agent, and a memory engine underneath with budget-aware recall, consolidation, conflict detection, and forgetting — running 24/7 on a Hugging Face Space. Mnemo: the Slack teammate that remembers, everywhere. Thanks for watching."

---

**Upload:** YouTube, public (or unlisted is NOT enough — rules say publicly visible), title "Mnemo — a Slack teammate that remembers | Slack Agent Builder Challenge". Paste the link in Devpost.
