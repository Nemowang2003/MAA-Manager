from flask import Flask, abort
from datetime import datetime, timedelta
from pathlib import Path
import json
import signal
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage

SAVED = Path("example.saved.json")

if SAVED.exists():
    with SAVED.open() as file:
        LAST_ACTION = json.load(file)
else:
    LAST_ACTION = dict()

CONFIG = Path("example.config.json")

if CONFIG.exists():
    with CONFIG.open() as file:
        config = json.load(file)
        smtp = SMTP_SSL if config["server"]["ssl"] else SMTP
        host = config["server"]["host"]
        port = config["server"].get("port", 0)
        SMTP_SERVER = smtp(host=host, port=port)
        username = config["auth"]["username"]
        password = config["auth"]["password"]
        SMTP_SERVER.login(username, password)

else:
    SMTP_SERVER = None

WAITING_MAIL = set()


def sigterm_handler(signalnum, frame):
    """Save `LAST_ACCESS` before exit."""
    with SAVED.open("w") as file:
        json.dump(LAST_ACTION, file)
    exit(0)


# register SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)

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
        WAITING_MAIL.add(user)
        action, time = _
        duration = datetime.now() - datetime.fromisoformat(time)
        return f"MAA last {action} {display(duration)}ago.\n"
    else:
        return "MAA has no action since the server started.\n"


def send_mail(user: str):
    if SMTP_SERVER is None:
        return
    msg = EmailMessage()
    msg.set_content(f"{user} has just offline.")
    msg["Subject"] = "MAA-Manager Offline Notice"
    msg["From"] = msg["To"] = username
    SMTP_SERVER.send_message(msg)


@app.route("/report/<user>/<action>")
def report(user, action):
    if action not in ("online", "offline"):
        abort(404)
    if user in WAITING_MAIL:
        send_mail(user)
        WAITING_MAIL.remove(user)
    LAST_ACTION[user] = (action, str(datetime.now()))
    return ""
