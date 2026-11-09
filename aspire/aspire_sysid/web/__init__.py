"""The web app of interactive operation: ``aspire web`` and ``aspire session --web``.

A browser front end for the interactive session and the task interview, served on this computer
only. It is a third way to conduct the same session as on the terminal: :mod:`.app` holds the state,
the channel to the user and the live progress, :mod:`.server` the local HTTP server and the
commands, :mod:`.page` the page.
"""

from .app import App, WebChannel, WebProgress, check_definition_text
from .server import WebServer, cmd_web, serve_session

__all__ = ["App", "WebChannel", "WebProgress", "WebServer", "check_definition_text", "cmd_web", "serve_session"]
