# Devpost submission — copy-paste kit

> Form: https://slackhack.devpost.com/ → Enter a submission
> Deadline: **July 13, 2026 @ 5:00pm PDT** (judging Jul 14 – Aug 6)

## Project name

**Mnemo — a Slack teammate that remembers**

## Elevator pitch (tagline, ~200 chars)

Long-term memory for Slack: Mnemo remembers what matters, recalls only what fits a token budget, and "sleeps" to consolidate and forget — with the token savings shown in every reply.

## Track

**Best New Slack Agent**

## Required technology used

**Slack AI capabilities** — the agent lives in Slack's AI Assistant pane (Agents & Assistants APIs: `assistant_thread_started`, suggested prompts, live status), plus slash commands, a message shortcut, and channel mentions via Bolt for Python over Socket Mode.

## About the project (long description)

### Inspiration

Every Slack bot has amnesia. You tell it your deadline on Monday and it's a stranger by Thursday. The obvious fix — replay the whole conversation history into every prompt — makes the bot slower, costlier, and noisier the longer you use it. Human memory doesn't work that way: we keep what's important, we compress experiences into knowledge while we sleep, and we forget the rest. Mnemo brings that lifecycle to a Slack workspace.

### What it does

Mnemo is a Slack-native memory teammate:

- **AI Assistant pane** — chat naturally; Mnemo recalls relevant memories *under a hard token budget*, answers from them, and writes new facts back. Every reply includes its accounting: memories used, context tokens spent, and % smaller than dumping full history.
- **/remember, /recall, /sleep** — explicit controls: store a fact, inspect exactly what the agent would recall about a topic, and trigger a "sleep" pass.
- **"Remember this" message shortcut** — save any teammate's message to memory in two clicks.
- **@mnemo in channels** — channels get their own *shared* memory, fully separate from each user's private memory (namespaced per user / per channel, per team).

The differentiator is the memory lifecycle, not just storage:

1. **Budget-aware recall** — memories are ranked by embedding relevance × importance and greedy-packed into a token budget, so context stays small and cheap forever.
2. **Salience-scored write-back** — identity, preferences, deadlines, and numbers score higher than chit-chat.
3. **Sleep-time consolidation** — related episodic memories are clustered and LLM-summarized into durable semantic facts; the raw events are demoted.
4. **Forgetting** — memories decay on a half-life curve (episodic ~7 days; semantic ~6× slower) and low-value ones are pruned, so the store never grows without bound.

### How we built it

- **Slack layer:** Bolt for Python + the Assistant class (AI Assistant pane, suggested prompts, `set_status`), slash commands, message shortcut, and `app_mention` events — all over Socket Mode, so no public endpoint is needed. App defined by a checked-in manifest for one-paste reproduction.
- **Memory engine:** pure Python, zero Slack imports (`mnemo/`): a memory store with episodic/semantic kinds, cosine retrieval modulated by importance and access frequency, greedy budget packing, clustering + LLM summarization for consolidation, and time-decay pruning.
- **LLM:** provider-agnostic OpenAI-compatible client — Gemini 2.5 Flash by default (free tier), OpenAI/Qwen via env, and a deterministic offline fallback so the whole system runs and self-tests with **zero API keys**.
- **Deployment:** Docker on a Hugging Face Space running 24/7 (bot thread + health endpoint), with a scheduled GitHub Action keep-alive and memory snapshots synced to a private HF dataset so memory survives container rebuilds.

### Challenges we ran into

- Making recall *provably* cheap: we return the full accounting (tokens used vs. full-history tokens) from the store so the UI can show real compression numbers instead of vibes.
- Memory hygiene across surfaces: DMs must stay private while channels share memory — solved with per-team/user/channel namespaces and one isolated store per namespace.
- Free-tier hosting for a bot that must run for a 3-week judging window: Socket Mode + health-endpoint keep-alive + snapshot restore on reboot.

### Accomplishments we're proud of

- A memory lifecycle (remember → recall → consolidate → forget), not just a vector dump.
- Visible token accounting in every reply — you can watch the budget work.
- The engine runs, demos, and self-tests entirely offline; the LLM is a plug-in, not a dependency.

### What we learned

Slack's Assistant APIs (threads, suggested prompts, live status) make an agent feel native for very little code — the hard part, and the differentiator, is what your agent does *between* messages. Sleep-time compute is that in miniature: the workspace's memory literally gets better while nobody is talking to it.

### What's next for Mnemo

- Automatic nightly sleep passes per namespace (no `/sleep` needed).
- An MCP server over the engine so any MCP-capable agent shares the same workspace memory.
- Channel digests: "here's what this channel learned this week," generated from fresh semantic memories.

## Built with

`python` · `slack-bolt` · `slack-agents-assistants` · `socket-mode` · `gemini` · `docker` · `hugging-face-spaces` · `github-actions`

## Links to include on the form

- **Space (running app + code):** https://huggingface.co/spaces/HIMANSHUKUMARJHA/mnemo
- **GitHub mirror:** https://github.com/himanshu748/mnemo
- **Health check:** https://himanshukumarjha-mnemo.hf.space
- **Demo video:** _(YouTube link — record per VIDEO_SCRIPT.md, must be < 3:00 and public)_
- **Slack sandbox URL:** _(your sandbox workspace URL — invite slackhack@salesforce.com and testing@devpost.com first)_
- **Architecture diagram:** upload `assets/architecture.png`
