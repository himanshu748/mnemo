# Demo video script — target 2:40 (hard limit 3:00)

**Setup before recording:** clean sandbox workspace, Mnemo installed and green; one public channel `#project-atlas` with mnemo invited; Assistant pane empty (fresh user or after wiping the data dir); screen recorder at 1080p; mic ready. Kill notifications (macOS Focus mode).

**Rule from Devpost:** no copyrighted music, video must show the real project functioning.

---

### 0:00–0:20 — Hook (Assistant pane visible, empty)

> "Every Slack bot has amnesia. Tell it your deadline today — tomorrow it's a stranger. And the usual fix, replaying your entire history into every prompt, gets slower and more expensive every day. This is Mnemo: a Slack teammate with an actual memory lifecycle. Watch."

### 0:20–1:00 — Teach it, then test it (Assistant pane)

Type, one after another:

1. `Remember that our API gateway migration ships July 22, and staging freezes 3 days before.`
2. `I prefer answers as short bullet points.`
3. Then ask a **paraphrase**, not the same words: `When do we need to stop merging to staging?`

> "I never said 'stop merging' — Mnemo recalled the freeze rule and did the date math. And look at the footer: it answered from 2 memories, ~40 context tokens — not my whole chat history. That accounting is in every reply."

*(Zoom/point at the footer: "recalled N memories · N context tokens · % smaller".)*

### 1:00–1:30 — Explicit controls (any channel or DM)

- `/remember The client demo login is demo@acme.test` → show the confirmation + store stats.
- `/recall demo` → show it surfaces the right fact.

> "Slash commands give you direct control — remember stores a fact, recall shows you exactly what the agent would retrieve, under the same token budget."

- Hover a teammate's message → ⋯ → **Remember this**.

> "Any message in Slack can become memory in two clicks."

### 1:30–2:05 — The differentiator: /sleep (Assistant pane or DM)

First add 2–3 related facts quickly (e.g. `/remember Standup moved to 9:30`, `/remember Standup is now on Zoom not Meet`, `/remember Ravi runs standup on Fridays`). Then:

- `/sleep`

> "This is what makes Mnemo different. Like a brain during sleep, it clusters related raw memories and compresses them into one durable fact — and low-value stale memories decay and get pruned. Memory that gets *better* while nobody's talking to it. That's why the context stays small forever."

*(Show the response: "consolidated N, pruned N", read the consolidated fact aloud.)*

### 2:05–2:25 — Shared channel memory

In `#project-atlas`: `@mnemo what do you know about this project?`

> "Channels get shared team memory — separate from everyone's private memory. What the team teaches Mnemo here, the whole team can recall here."

### 2:25–2:40 — Close (architecture diagram on screen)

> "Bolt for Python on Slack's Agents and Assistants APIs, Socket Mode, a pure-Python memory engine with budget-aware recall, consolidation and forgetting — running 24/7 on a Hugging Face Space. Mnemo: the Slack teammate that remembers. Thanks for watching."

---

**Upload:** YouTube, public (or unlisted is NOT enough — rules say publicly visible), title "Mnemo — a Slack teammate that remembers | Slack Agent Builder Challenge". Paste the link in Devpost.
