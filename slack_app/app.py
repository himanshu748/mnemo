"""Mnemo for Slack — Bolt app.

Surfaces:
  * AI Assistant pane: chat with memory (Slack "Agents & Assistants" feature).
  * /remember <text>  — store a fact.
  * /recall <query>   — see what Mnemo recalls (budget-aware).
  * /sleep            — consolidate + forget (sleep-time pass).
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


def _ns(team_id=None, user_id=None, channel_id=None) -> str:
    """Namespace memory: public channels are shared (per-channel); everything
    else (DMs / assistant threads) is private (per-user)."""
    team = team_id or "team"
    if channel_id and str(channel_id).startswith("C"):
        return "%s:channel:%s" % (team, channel_id)
    return "%s:user:%s" % (team, user_id or "anon")


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
