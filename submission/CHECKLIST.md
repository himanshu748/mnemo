# Submission checklist — Slack Agent Builder Challenge

Deadline: **Sun Jul 13, 2026, 5:00pm PDT** · Judging: **Jul 14 – Aug 6** (app must stay up the whole time)

## Deployment (do first — bot must be live)

- [ ] Space secrets set (Settings → Variables and secrets): `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`
- [ ] `MNEMO_TOKEN_SECRET` set (any random string — `openssl rand -hex 32` works) so `/mnemo-token` and the MCP server can mint/verify tokens
- [ ] Optional but recommended: `MNEMO_HF_DATASET=HIMANSHUKUMARJHA/mnemo-memory` (variable) + `HF_TOKEN` (secret, a **fine-grained token with write access to that dataset only**) so memory survives rebuilds
- [ ] Space is Running: https://himanshukumarjha-mnemo.hf.space shows "Mnemo is running" (200, not 503)
- [ ] Keep-alive Action enabled on the GitHub mirror (Actions tab → keep-space-awake → enable, run once manually)
- [ ] End-to-end smoke test in Slack: Assistant pane answer + `/remember` + `/recall` + `/sleep` + `@mnemo` in a channel
- [ ] Conflict test: `/remember Standup is at 9am.` then `/remember Standup is at 9:30am.` then `/sleep` → should post a ⚠️ conflict message in-channel, not silently merge
- [ ] MCP test: `/mnemo-token` in Slack → add `https://himanshukumarjha-mnemo.hf.space/mcp` as an MCP server in Claude Desktop/Code → paste the token → ask it about a fact you taught Mnemo in Slack and confirm it recalls it

## Sandbox for judges (required)

- [ ] Create/confirm a dedicated sandbox workspace with Mnemo installed (Slack developer sandbox via https://api.slack.com/developer-program if you don't have one)
- [ ] Invite **slackhack@salesforce.com** and **testing@devpost.com** to the workspace
- [ ] Seed it lightly: a `#project-…` channel with mnemo added and 2–3 remembered facts so judges see recall immediately
- [ ] Copy the workspace URL for the Devpost form

## Video (required, <3:00, public)

- [ ] Record per `submission/VIDEO_SCRIPT.md`
- [ ] Under 3 minutes, shows the real app working, no copyrighted music
- [ ] Upload to YouTube as **Public**, link pasted into Devpost AND into README + DEVPOST.md

## Devpost form (required)

- [ ] Track: **Best New Slack Agent**
- [ ] Text description: paste from `submission/DEVPOST.md`
- [ ] Architecture diagram: upload `assets/architecture.png`
- [ ] Video link, sandbox URL, Space + GitHub links
- [ ] Team/eligibility fields, submit before the deadline (don't wait for the last hour)

## Nice-to-have (only if time remains)

- [ ] 2–3 screenshots (Assistant pane with the token footer, `/sleep` conflict message, an MCP client answering from Slack memory) for the Devpost gallery
- [ ] Pin the Space + add a thumbnail image on the Space settings
- [ ] Nightly auto-sleep pass (cron thread in launcher) — mentioned as "what's next", shipping it is a bonus
