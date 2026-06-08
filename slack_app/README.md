# Mnemo for Slack

A Slack teammate with **long-term memory**. Mnemo remembers salient facts per
user and per channel, recalls the *minimal critical set* under a token budget,
and runs **sleep-time consolidation + forgetting** so memory stays sharp and
cheap. Built on the [Mnemo engine](../README.md); model-agnostic (Gemini free
tier recommended).

> Hackathon: **Slack Agent Builder Challenge** · "New Slack Agent" track.

## What it does in Slack

| Surface | Behavior |
|---|---|
| **AI Assistant pane** | Chat with memory. Mnemo retrieves under budget, answers, and writes new facts back. Each reply shows how many memories it used and how much smaller the context was vs. dumping full history. |
| `/remember <text>` | Store a fact explicitly. |
| `/recall <query>` | See what Mnemo recalls about a topic (budget-aware). |
| `/sleep` | Run a consolidation + forgetting pass. |
| **"Remember this"** message shortcut | Save any message to memory. |
| `@mnemo` in a channel | Channel-scoped memory chat (shared team memory). |

Memory is namespaced: DMs/assistant threads are **private per user**; public
channels are **shared per channel**.

## Setup (~5 min, all free, works from India)

1. **Create the app**: https://api.slack.com/apps → *Create New App* → *From a
   manifest* → paste [`manifest.yaml`](manifest.yaml).
2. **Install to workspace** and copy the **Bot token** (`xoxb-…`).
3. Enable **Socket Mode** (Settings → Socket Mode) and create an **App-level
   token** (`xapp-…`) with `connections:write`.
4. **Gemini key** (free): https://aistudio.google.com/apikey
5. Configure and run:

```bash
pip install -r ../requirements.txt
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=...
python3 -m slack_app.app          # connects via Socket Mode — no public URL needed
```

Verify the wiring without Slack at all:

```bash
python3 -m slack_app.app --selftest
```

## Deploy (for a persistent demo)

Socket Mode runs fine from anywhere, including a free **Hugging Face Space** or
any always-on box — just set the four env vars and run the same command. No
public endpoint or cloud account required.

## Judging access

At submission, install the app to a sandbox workspace and invite the judges
(`slackhack@salesforce.com`, `testing@devpost.com`) so they can try the
Assistant pane and slash commands.
