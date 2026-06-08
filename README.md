---
title: Mnemo
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Mnemo — a Slack teammate with long-term memory

Budget-aware recall, sleep-time consolidation, and forgetting, running on Gemini.
This Space runs the bot 24/7 over Slack Socket Mode (plus a tiny health endpoint).

**Required Space secrets** (Settings → Variables and secrets):
`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `GEMINI_API_KEY`, `LLM_PROVIDER=gemini`.

Built for the Slack Agent Builder Challenge. Source: the Mnemo engine + `slack_app/` Bolt app.
