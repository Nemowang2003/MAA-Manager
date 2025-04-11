from flask import Flask, abort, request
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import json
import atexit
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage

SAVED = Path("config/saved.json")

if SAVED.exists():
    with SAVED.open() as file:
        LAST_ACTION = json.load(file)
else:
    LAST_ACTION = dict()


@dataclass
class MailSender:
    host: str
    port: int
    ssl: bool
    username: str
    password: str

    OFFLINE = "{} has just offline."
    DAILY_ERROR = "{} has some trouble with daily sign-in."

    def __post_init__(self):
        self._msg = EmailMessage()
        self._msg["From"] = self._msg["To"] = self.username
        # check connection
        self.smtp_server()

    def smtp_server(self) -> SMTP | SMTP_SSL:
        smtp = SMTP_SSL if self.ssl else SMTP
        smtp_server = smtp(self.host, self.port)
        smtp_server.login(self.username, self.password)
        return smtp_server

    def send_offline(self, user: str):
        del self._msg["Subject"]
        self._msg["Subject"] = "MAA-Manager Offline Notice"
        self._msg.set_content(self.OFFLINE.format(user))
        with self.smtp_server() as smtp_server:
            smtp_server.send_message(self._msg)

    def send_daily_error(self, user: str):
        del self._msg["Subject"]
        self._msg["Subject"] = "MAA-Manager Daily-Sign Error"
        self._msg.set_content(self.DAILY_ERROR.format(user))
        with self.smtp_server() as smtp_server:
            smtp_server.send_message(self._msg)


CONFIG = Path("config/config.json")

MAIL_SENDER: MailSender | None

if CONFIG.exists():
    with CONFIG.open() as file:
        config = json.load(file)
        mail = config["mail-sender"]
        MAIL_SENDER = MailSender(
            host=mail["host"],
            port=mail.get("port", 0),
            ssl=mail.get("ssl", False),
            username=mail["username"],
            password=mail["password"],
        )
WAITING_MAIL = set()


def at_exit():
    """Save `LAST_ACCESS` before exit."""
    with SAVED.open("w") as file:
        json.dump(LAST_ACTION, file)


# register
atexit.register(at_exit)

app = Flask(__name__)


def display(duration: timedelta) -> str:
    """Display`timedelta` with a better format."""

    def format(amount: int, unit: str):
        return f"{amount} {unit}" + ("s " if abs(amount) != 1 else " ")

    msg = ""

    if duration.days:
        msg += format(duration.days, "day")

    hour = duration.seconds // 3600
    if hour:
        msg += format(hour, "hour")
    elif msg:  # implies hour is 0
        msg += "0 hours "

    minute = duration.seconds % 3600 // 60
    if minute:
        msg += format(minute, "minute")
    elif msg:  # implies minute is 0
        msg += "0 minutes "

    second = duration.seconds % 60
    msg += format(second, "second")

    return msg


@app.route("/query/<user>")
def query(user):
    if _ := LAST_ACTION.get(user):
        action, time = _
        if action == "online":
            WAITING_MAIL.add(user)
        duration = datetime.now() - datetime.fromisoformat(time)
        return f"MAA last {action} {display(duration)}ago.\n"
    else:
        return "MAA has no action since the server started.\n"


@app.route("/report/<user>/<action>")
def report(user, action):
    if action not in ("online", "offline"):
        abort(404)
    if action == "offline" and user in WAITING_MAIL:
        MAIL_SENDER.send_offline(user)
        WAITING_MAIL.remove(user)
    LAST_ACTION[user] = (action, str(datetime.now()))
    return ""
