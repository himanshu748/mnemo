# Devpost submission — copy-paste kit

> Form: https://slackhack.devpost.com/ → Enter a submission
> Deadline: **July 13, 2026 @ 5:00pm PDT** (judging Jul 14 – Aug 6)

## Project name

**Mnemo — a Slack teammate that remembers**

## Elevator pitch (tagline, ~200 chars)

Long-term memory for Slack: Mnemo remembers what matters, recalls only what fits a token budget, flags contradictions instead of hiding them, and follows you into Claude via MCP — same memory, everywhere.

## Track

**Best New Slack Agent**

## Required technology used

Two of the three:

1. **Slack AI capabilities** — the agent lives in Slack's AI Assistant pane (Agents & Assistants APIs: `assistant_thread_started`, suggested prompts, live status), plus slash commands, a message shortcut, and channel mentions via Bolt for Python over Socket Mode.
2. **MCP server integration** — the same memory engine is exposed as an MCP server (`/mcp`, streamable-HTTP transport), so Claude Desktop, Claude Code, or any MCP client can `remember`/`recall`/`chat`/`sleep` against a user's own memory — the exact store their Slack account writes to, authenticated by a token minted with `/mnemo-token`.

## About the project (long description)

### Inspiration

Every Slack bot has amnesia. You tell it your deadline on Monday and it's a stranger by Thursday. The obvious fix — replay the whole conversation history into every prompt — makes the bot slower, costlier, and noisier the longer you use it. Human memory doesn't work that way: we keep what's important, we compress experiences into knowledge while we sleep, and we forget the rest. Mnemo brings that lifecycle to a Slack workspace.

### What it does

Mnemo is a Slack-native memory teammate:

- **AI Assistant pane** — chat naturally; Mnemo recalls relevant memories *under a hard token budget*, answers from them, and writes new facts back. Every reply includes its accounting: memories used, context tokens spent, and % smaller than dumping full history.
- **/remember, /recall, /sleep** — explicit controls: store a fact, inspect exactly what the agent would recall about a topic, and trigger a "sleep" pass.
- **"Remember this" message shortcut** — save any teammate's message to memory in two clicks.
- **@mnemo in channels** — channels get their own *shared* memory, fully separate from each user's private memory (namespaced per user / per channel, per team).
- **/mnemo-token + MCP** — mint a personal token and add Mnemo as an MCP server in Claude Desktop or Claude Code; it reads and writes the exact same memory Slack sees.

The differentiator is the memory lifecycle, not just storage:

1. **Budget-aware recall** — memories are ranked by embedding relevance × importance and greedy-packed into a token budget, so context stays small and cheap forever.
2. **Salience-scored write-back** — identity, preferences, deadlines, and numbers score higher than chit-chat.
3. **Sleep-time consolidation** — related episodic memories are clustered; agreeing ones are LLM-summarized into durable semantic facts and the raw events are demoted.
4. **Conflict detection** — clusters that *disagree* (a time, date, or decision with two different values) are flagged back to the channel instead of silently merged — a feature that only makes sense for *shared team* memory, not a personal notes app.
5. **Forgetting** — memories decay on a half-life curve (episodic ~7 days; semantic ~6× slower) and low-value ones are pruned, so the store never grows without bound.

### How we built it

- **Slack layer:** Bolt for Python + the Assistant class (AI Assistant pane, suggested prompts, `set_status`), slash commands, message shortcut, and `app_mention` events — all over Socket Mode, so no public endpoint is needed. App defined by a checked-in manifest for one-paste reproduction.
- **Memory engine:** pure Python, zero Slack imports (`mnemo/`): a memory store with episodic/semantic kinds, cosine retrieval modulated by importance and access frequency, greedy budget packing, clustering + LLM summarization for consolidation, agree/conflict classification, and time-decay pruning.
- **MCP surface:** `mnemo/mcp_server.py` exposes the same engine over streamable-HTTP, mounted alongside the health check in one ASGI app. Auth is a stateless HMAC token (`mnemo/tokens.py`) binding a caller to their Slack `team:user` namespace — no token database, and it resolves to the *exact* namespace string the Slack side uses, verified end-to-end so a Slack-written memory shows up over MCP and vice versa.
- **LLM:** provider-agnostic OpenAI-compatible client — Gemini 2.5 Flash by default (free tier), OpenAI/Qwen via env, and a deterministic offline fallback (including for conflict classification) so the whole system runs and self-tests with **zero API keys**.
- **Deployment:** Docker on a Hugging Face Space running 24/7 (bot thread + one ASGI app for health + MCP), with a scheduled GitHub Action keep-alive and memory snapshots synced to a private HF dataset so memory survives container rebuilds.

### Challenges we ran into

- Making recall *provably* cheap: we return the full accounting (tokens used vs. full-history tokens) from the store so the UI can show real compression numbers instead of vibes.
- Telling *disagreement* from *paraphrase*: cosine similarity alone can't distinguish "standup is at 9am" from "standup is at 9:30am" — they're topically identical. We added an LLM (and offline heuristic) classification pass specifically for that.
- Keeping two independent surfaces (Slack, MCP) from caching two different views of the same memory in one process — solved with a process-wide router singleton keyed by data directory, and caught by an end-to-end test that writes through one surface and reads through the other.
- Free-tier hosting for a bot that must run for a 3-week judging window: Socket Mode + health-endpoint keep-alive + snapshot restore on reboot.

### Accomplishments we're proud of

- A memory lifecycle (remember → recall → consolidate → flag conflicts → forget), not just a vector dump.
- The same memory follows you off Slack — teach Mnemo something in Slack, ask Claude Desktop about it a minute later.
- Visible token accounting in every reply — you can watch the budget work.
- The engine runs, demos, and self-tests entirely offline, including conflict detection; the LLM is a plug-in, not a dependency.

### What we learned

Slack's Assistant APIs (threads, suggested prompts, live status) make an agent feel native for very little code — the hard part, and the differentiator, is what your agent does *between* messages, and how far its memory reaches beyond the one app that wrote it.

### What's next for Mnemo

- Automatic nightly sleep passes per namespace (no `/sleep` needed).
- Push conflict alerts and consolidated digests as scheduled channel messages, not just `/sleep` output.
- More MCP tools: search across a whole channel's semantic memory, not just one namespace at a time.

## Built with

`python` · `slack-bolt` · `slack-agents-assistants` · `socket-mode` · `mcp` · `gemini` · `docker` · `hugging-face-spaces` · `github-actions`

## Links to include on the form

- **Space (running app + code):** https://huggingface.co/spaces/HIMANSHUKUMARJHA/mnemo
- **GitHub mirror:** https://github.com/himanshu748/mnemo
- **Health check:** https://himanshukumarjha-mnemo.hf.space
- **Demo video:** _(YouTube link — record per VIDEO_SCRIPT.md, must be < 3:00 and public)_
- **Slack sandbox URL:** _(your sandbox workspace URL — invite slackhack@salesforce.com and testing@devpost.com first)_
- **Architecture diagram:** upload `assets/architecture.png`
