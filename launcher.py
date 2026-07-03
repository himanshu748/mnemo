"""HF Space entrypoint: run the Mnemo Slack bot (Socket Mode) in a background
thread, and serve a tiny health endpoint on the Space port so the Space stays
'running'. The health text reports real bot state — if the bot thread died or
secrets are missing, it says so instead of pretending all is well."""
import os
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STATUS = {"bot": "starting"}


def run_bot():
    try:
        from slack_app.app import build_app
        from slack_bolt.adapter.socket_mode import SocketModeHandler
        app, glue = build_app()
        STATUS["bot"] = "connected (backend: %s)" % glue.backend()
        print("Mnemo bot starting. backend:", glue.backend(), flush=True)
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
        STATUS["bot"] = "disconnected"
    except KeyError as exc:
        STATUS["bot"] = "NOT configured - missing Space secret %s" % exc
        print("Bot not started:", STATUS["bot"], flush=True)
    except Exception as exc:
        STATUS["bot"] = "CRASHED: %s" % exc
        print("Bot crashed:", exc, flush=True)


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = STATUS["bot"].startswith("connected")
        body = ("Mnemo is running. Talk to the bot in Slack. [bot: %s]" if ok
                else "Mnemo health server is up, but the bot is not: %s") % STATUS["bot"]
        self.send_response(200 if ok else 503)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", "7860"))
    print("Health server listening on", port, flush=True)
    HTTPServer(("0.0.0.0", port), Health).serve_forever()
