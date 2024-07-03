from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from ssl import SSLContext, PROTOCOL_TLS_SERVER
from urllib.parse import urlparse, parse_qsl
from datetime import datetime, timedelta
from typing import Dict

ADDR = ("0.0.0.0", 4573)
QUERY = "/query"
REPORT = "/report"
LAST_ACCESS: Dict[str, datetime] = dict()


def display(timedelta: timedelta) -> str:
    """Display`timedelta` with a better format."""

    def format(amount: int, unit: str):
        return f"{amount} {unit}" + "s " if abs(amount) != 1 else " "

    msg = ""

    if timedelta.days:
        msg += format(timedelta.days, "day")

    hour = timedelta.seconds // 3600
    if hour:
        msg += format(hour, "hour")
    elif msg:  # implies hour is 0
        msg += "0 hours "

    minute = timedelta.seconds % 3600 // 60
    if minute:
        msg += format(minute, "minute")
    elif msg:  # implies minute is 0
        msg += "0 minutes "

    second = timedelta.seconds % 60
    msg += format(second, "second")

    return msg


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        content = urlparse(self.path)
        query = parse_qsl(content.query)
        if content.path != QUERY or len(query) != 1 or query[0][0] != "user":
            self.unsupported()
            return

        user = query[0][1]
        if last_time := LAST_ACCESS.get(user):
            payload = (
                f"MAA last online {display(datetime.now() - last_time)}ago.\n".encode()
            )
        else:
            payload = "MAA hasn't logged in since the server started.\n".encode()

        self.send_response(HTTPStatus.OK)
        self.send_header("Connection", "close")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != REPORT:
            self.unsupported()
            return

        if content := self.rfile.read(int(self.headers.get("Content-Length"))).decode():
            self.log_message(content)
            LAST_ACCESS[content] = datetime.now()

        self.send_response(HTTPStatus.OK)
        self.send_header("Connection", "close")
        self.send_header("Content-Length", 0)
        self.end_headers()

    def unsupported(self):
        self.send_error(
            HTTPStatus.NOT_IMPLEMENTED, f"Unsupported method ({self.command})"
        )

    def version_string(self):
        return "Handmade :)"

    def date_time_string(self):
        return "I don't know :("


with TCPServer(ADDR, Handler) as server:
    context = SSLContext(PROTOCOL_TLS_SERVER)
    context.load_cert_chain("example.crt", "example.key")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
