"""Mnemo for Slack — Bolt app.

Surfaces:
  * AI Assistant pane: chat with memory (Slack "Agents & Assistants" feature).
  * /remember <text>  — store a fact.
  * /recall <query>   — see what Mnemo recalls (budget-aware).
  * /sleep            — consolidate + forget (sleep-time pass).
  * /mnemo-token      — mint a token to connect the same memory over MCP.
  * "Remember this" message shortcut — store any message.
  * @mention in a channel — channel-scoped memory chat.

Run (Socket Mode, easiest for judging — no public URL needed):
    python3 -m slack_app.app                 # needs SLACK_BOT_TOKEN + SLACK_APP_TOKEN
Self-test the memory wiring without Slack:
    python3 -m slack_app.app --selftest
"""
from __future__ import annotations

import os
import sys

from slack_app.glue import SlackMemoryGlue  # no slack dependency
from mnemo.namespace import channel_ns, user_ns

MCP_URL = os.environ.get("MNEMO_MCP_URL", "https://himanshukumarjha-mnemo.hf.space/mcp")


def _ns(team_id=None, user_id=None, channel_id=None) -> str:
    """Namespace memory: public channels are shared (per-channel); everything
    else (DMs / assistant threads) is private (per-user). Shared with the MCP
    surface (mnemo/tokens.py) so a Slack user and their own MCP client land on
    the exact same private store."""
    if channel_id and str(channel_id).startswith("C"):
        return channel_ns(team_id or "team", channel_id)
    return user_ns(team_id or "team", user_id)


def build_app():
    from slack_bolt import App, Assistant

    glue = SlackMemoryGlue(token_budget=int(os.environ.get("MNEMO_TOKEN_BUDGET", "400")),
                           data_dir=os.environ.get("MNEMO_DATA_DIR", "data"))
    kwargs = {"token": os.environ["SLACK_BOT_TOKEN"]}
    if os.environ.get("SLACK_SIGNING_SECRET"):
        kwargs["signing_secret"] = os.environ["SLACK_SIGNING_SECRET"]
    app = App(**kwargs)
    assistant = Assistant()

    @assistant.thread_started
    def _started(say, set_suggested_prompts):
        say("Hi! I'm *Mnemo* — I remember what matters across our chats, and I "
            "keep the context small so it stays cheap. Tell me things to remember, "
            "or ask what I know.")
        set_suggested_prompts(prompts=[
            {"title": "What do you remember about me?",
             "message": "What do you remember about me?"},
            {"title": "Remember a fact", "message": "Remember that "},
        ])

    @assistant.user_message
    def _on_message(payload, context, set_status, say):
        set_status("thinking…")
        ns = _ns(context.get("team_id"), context.get("user_id"), context.get("channel_id"))
        out = glue.chat(ns, payload.get("text", ""))
        print("[assistant] q=%r -> %r (%d mem, %d ctx-tokens)" % (
            payload.get("text", ""), out["reply"][:80],
            len(out["used_memories"]), out["tokens_used"]), flush=True)
        footer = ("\n\n_recalled %d memories · %d context tokens "
                  "(%.0f%% smaller than full history)_" % (
                      len(out["used_memories"]), out["tokens_used"],
                      100 * out["compression"]))
        say(out["reply"] + footer)

    app.assistant(assistant)

    @app.command("/remember")
    def _remember(ack, command, respond):
        ack()
        text = (command.get("text") or "").strip()
        if not text:
            respond("Usage: `/remember <something to remember>`")
            return
        ns = _ns(command.get("team_id"), command.get("user_id"), command.get("channel_id"))
        glue.remember(ns, text)
        respond("Got it — I'll remember that. _(%s)_" % glue.stats(ns))

    @app.command("/recall")
    def _recall(ack, command, respond):
        ack()
        query = (command.get("text") or "").strip()
        ns = _ns(command.get("team_id"), command.get("user_id"), command.get("channel_id"))
        sel = glue.recall(ns, query)["selected"]
        if not sel:
            respond("I don't have anything on that yet.")
            return
        respond("Here's what I recall:\n" + "\n".join("• %s" % it.text for it in sel))

    @app.command("/sleep")
    def _sleep(ack, command, respond):
        ack()
        ns = _ns(command.get("team_id"), command.get("user_id"), command.get("channel_id"))
        rep = glue.sleep(ns)
        respond("Slept 😴 — consolidated %d, pruned %d. Now: _%s_" % (
            len(rep["consolidated"]), rep["pruned_count"], rep["after"]))
        for c in rep.get("conflicts", []):
            bullets = "\n".join("• %s" % t for t in c["texts"])
            respond(
                text=("⚠️ *Conflicting memories* — these don't agree, so I kept "
                      "both instead of merging them:\n%s\nLet me know which is "
                      "current with `/remember <the correct fact>`." % bullets),
                response_type="in_channel",
            )

    @app.command("/mnemo-token")
    def _mnemo_token(ack, command, respond):
        ack()
        from mnemo.tokens import mint
        team_id = command.get("team_id") or "team"
        user_id = command.get("user_id")
        token = mint(team_id, user_id)
        respond(
            "🔑 Your personal Mnemo MCP token — keep it private, it unlocks "
            "*your* memory (the exact same one this Slack account uses):\n"
            "```%s```\n"
            "1. Add Mnemo as an MCP server: `claude mcp add --transport http mnemo %s`\n"
            "2. Tell it once: “My mnemo token is %s — use it for every mnemo tool call.”\n"
            "Then just talk to it — it reads and writes the exact memory Slack sees."
            % (token, MCP_URL, token)
        )

    @app.shortcut("remember_message")
    def _remember_message(ack, shortcut, context):
        ack()
        text = (shortcut.get("message") or {}).get("text", "")
        ch = (shortcut.get("channel") or {}).get("id")
        if text:
            glue.remember(_ns(context.get("team_id"), shortcut["user"]["id"], ch), text)

    @app.event("app_mention")
    def _mention(event, say, context):
        ns = _ns(context.get("team_id"), event.get("user"), event.get("channel"))
        say(glue.chat(ns, event.get("text", ""))["reply"])

    @app.event("message")
    def _ignore_message(logger):
        pass  # assistant middleware handles assistant-thread messages

    return app, glue


def selftest() -> None:
    import shutil
    shutil.rmtree("/tmp/mnemo_selftest", ignore_errors=True)  # always start fresh
    glue = SlackMemoryGlue(data_dir="/tmp/mnemo_selftest")
    ns = _ns("T1", "U1", None)
    glue.remember(ns, "I am allergic to penicillin.", 0.9)
    glue.remember(ns, "My dog's name is Biscuit.")
    out = glue.chat(ns, "What am I allergic to?")
    print("backend     :", glue.backend())
    print("namespace   :", ns)
    print("reply       :", out["reply"])
    print("ctx tokens  :", out["tokens_used"], "| compression:", round(out["compression"], 2))
    print("stats       :", glue.stats(ns))
    assert "penicillin" in out["reply"].lower(), "expected recall of the allergy fact"
    print("\nSELFTEST OK")

    # channel-shared memory + conflict detection (two teammates giving the
    # bot different answers to the same question)
    ns2 = _ns("T1", None, "C1")
    glue.remember(ns2, "Standup is at 9am.")
    glue.remember(ns2, "Standup is at 9:30am.")
    rep = glue.sleep(ns2)
    print("conflicts   :", rep["conflicts"])
    assert rep["conflicts"], "expected the two standup times to be flagged as conflicting"
    print("CONFLICT-DETECTION OK")

    # MCP surface: same private namespace as the Slack user above
    from mnemo.tokens import mint, verify
    os.environ.setdefault("MNEMO_TOKEN_SECRET", "selftest-secret")
    token = mint("T1", "U1")
    assert verify(token) == ns, "MCP token must resolve to the same namespace Slack uses"
    print("MCP TOKEN   : namespace matches Slack ✔")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app, glue = build_app()
    if os.environ.get("SLACK_APP_TOKEN"):
        from slack_bolt.adapter.socket_mode import SocketModeHandler
        print("Mnemo running via Socket Mode. backend:", glue.backend())
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    else:
        print("Set SLACK_APP_TOKEN to run in Socket Mode, or serve build_app()[0] "
              "over HTTP. See slack_app/README.md.")
