"""HF Space entrypoint. Runs three things in one process, sharing the
Space's single exposed port:

1. the Slack bot (Socket Mode) in a background thread
2. a health check at "/" that reports real bot state
3. the Mnemo MCP server (streamable-http) at "/mcp", so any MCP client
   (Claude Desktop, Claude Code, ...) can share the exact memory Slack sees
"""
import contextlib
import os
import threading
import logging

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


def build_web_app():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route, Mount

    from mnemo.mcp_server import mcp

    async def health(request):
        ok = STATUS["bot"].startswith("connected")
        body = (
            "Mnemo is running. Talk to the bot in Slack. [bot: %s] "
            "MCP endpoint: /mcp (get a token in Slack via /mnemo-token)."
        ) % STATUS["bot"] if ok else (
            "Mnemo health server is up, but the bot is not: %s" % STATUS["bot"]
        )
        return PlainTextResponse(body, status_code=200 if ok else 503)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        # FastMCP's streamable-http transport needs its session manager
        # actually running; mounting the sub-app alone doesn't start it.
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(mcp.session_manager.run())
            yield

    return Starlette(
        routes=[
            Route("/", health),               # exact "/" -> health
            Mount("/", app=mcp.streamable_http_app()),  # everything else -> MCP (serves "/mcp")
        ],
        lifespan=lifespan,
    )


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    print("Web server (health + MCP) listening on", port, flush=True)
    uvicorn.run(build_web_app(), host="0.0.0.0", port=port)
