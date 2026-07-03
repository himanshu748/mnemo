---
title: Mnemo
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
---

<div align="center">

# 🧠 Mnemo — a Slack teammate that remembers

**Long-term memory for your workspace: budget-aware recall, sleep-time consolidation, and honest forgetting — right inside Slack's AI Assistant pane.**

[![Slack AI](https://img.shields.io/badge/Slack-AI%20Assistant%20pane-4A154B?style=flat-square&logo=slack)](https://docs.slack.dev/ai/)
[![Bolt](https://img.shields.io/badge/framework-Bolt%20for%20Python-1f2d3d?style=flat-square)](https://tools.slack.dev/bolt-python/)
[![Runs on](https://img.shields.io/badge/runs%20on-HF%20Space%2C%2024%2F7-fbbf24?style=flat-square)](https://himanshukumarjha-mnemo.hf.space)
[![Selftest](https://img.shields.io/badge/selftest-passing-34d399?style=flat-square)](#run-it-yourself)

<sub>Built for the **[Slack Agent Builder Challenge](https://slackhack.devpost.com/)** · track: **Best New Slack Agent** · required tech used: **Slack AI capabilities** (Agents & Assistants)</sub>

</div>

---

## The problem

Every Slack bot has amnesia. You tell it your deadline, your stack, your customer's quirks — and next thread it knows nothing. The naive fix (stuff the whole history into every prompt) gets slower, costlier, and noisier every single day you use it.

**Mnemo treats memory as a budget, not a landfill.** It remembers what matters, recalls only the *minimal critical set* of memories under a hard token budget, and periodically "sleeps" — consolidating related raw events into durable facts and letting stale trivia decay away. Every reply shows its accounting: how many memories it used, how many context tokens that cost, and how much smaller that is than dumping full history.

## What it does in Slack

| Surface | Behavior |
|---|---|
| **🤖 AI Assistant pane** | Chat with memory. Mnemo retrieves under budget, answers, writes new facts back — and shows the token math in each reply. |
| `/remember <text>` | Store a fact explicitly. |
| `/recall <query>` | See exactly what Mnemo would recall about a topic (budget-aware). |
| `/sleep` | Run a consolidation + forgetting pass, and see what got merged and pruned. |
| **"Remember this" shortcut** | Save any message to memory from the ⋯ menu. |
| `@mnemo` in a channel | Channel-scoped chat — **shared team memory**, separate from your private one. |

Memory is namespaced: DMs and assistant threads are **private per user**; public channels are **shared per channel**. Nothing leaks across.

## Architecture

<img src="assets/architecture.svg" alt="Mnemo architecture" width="100%">

The memory engine (`mnemo/`) is pure Python with zero Slack dependencies — the Bolt app (`slack_app/`) is a thin surface over it:

1. **Budget-aware recall** — memories are ranked by embedding relevance × importance, then greedy-packed into a hard token budget (`MNEMO_TOKEN_BUDGET`, default 400).
2. **Write-back with salience** — every exchange is stored as an *episodic* memory with a heuristic importance score (identity, preferences, numbers, deadlines score higher).
3. **Sleep-time pass** — related episodic memories are clustered and LLM-summarized into durable *semantic* facts; raw events are demoted and low-value memories decay away on a half-life curve (7 days episodic, ~6× slower for semantic).
4. **Persistence** — one JSON store per namespace, saved after every write, optionally snapshotted to a private HF dataset so memory survives Space rebuilds.

The LLM is pluggable (any OpenAI-compatible endpoint — Gemini free tier by default, OpenAI or Qwen via env), and there's a deterministic offline fallback so everything runs and tests **without any API key**.

## Run it yourself

**1. Create the Slack app** — [api.slack.com/apps](https://api.slack.com/apps) → *Create New App* → *From a manifest* → paste [`slack_app/manifest.yaml`](slack_app/manifest.yaml). Install it to your workspace.

**2. Grab tokens** — the **Bot token** (`xoxb-…`) from *OAuth & Permissions*, and an **App-level token** (`xapp-…`) with `connections:write` from *Basic Information* (Socket Mode is already enabled by the manifest).

**3. Run** (locally, or set the same values as Space secrets):

```bash
pip install -r requirements.txt
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
export LLM_PROVIDER=gemini            # free key: https://aistudio.google.com/apikey
export GEMINI_API_KEY=...
python3 -m slack_app.app              # Socket Mode — no public URL needed
```

Verify the memory wiring with zero credentials:

```bash
python3 -m slack_app.app --selftest   # -> SELFTEST OK
```

### Space configuration

| Secret / variable | Required | Purpose |
|---|---|---|
| `SLACK_BOT_TOKEN` | ✅ | Bot token (`xoxb-…`) |
| `SLACK_APP_TOKEN` | ✅ | App-level token (`xapp-…`), Socket Mode |
| `GEMINI_API_KEY` + `LLM_PROVIDER=gemini` | ✅ | LLM + embeddings (free tier) |
| `MNEMO_HF_DATASET` | optional | e.g. `HIMANSHUKUMARJHA/mnemo-memory` — snapshot memory to a private dataset |
| `HF_TOKEN` | optional | write token for the snapshot dataset |

This Space runs the bot 24/7 over Socket Mode plus a tiny health endpoint (`/`) on port 7860; a scheduled GitHub Action pings it so the free Space never idles out.

## Repo layout

```
mnemo/        the memory engine (no Slack imports): store, agent, router, LLM client
slack_app/    Bolt app + manifest + glue layer (unit-testable without slack_bolt)
launcher.py   Space entrypoint: bot thread + health endpoint
assets/       architecture diagram
submission/   Devpost writeup, demo script, checklist
```

## Judging access

The app is installed in a sandbox workspace with `slackhack@salesforce.com` and `testing@devpost.com` invited. Try the Assistant pane first (tell it two facts, ask it back a paraphrase), then `/recall`, then `/sleep` to watch consolidation happen live.
