"""HF Space entrypoint: run the Mnemo Slack bot (Socket Mode) in a background
thread, and serve a tiny health endpoint on the Space port so the Space stays
'running'."""
import os
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_bot():
    from slack_app.app import build_app
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    app, glue = build_app()
    print("Mnemo bot starting. backend:", glue.backend(), flush=True)
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Mnemo is running. Talk to the bot in Slack.")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", "7860"))
    print("Health server listening on", port, flush=True)
    HTTPServer(("0.0.0.0", port), Health).serve_forever()
