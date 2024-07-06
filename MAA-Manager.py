from flask import Flask, abort
from datetime import datetime, timedelta
from pathlib import Path
import json
import signal

SAVED_FILE = Path("example.json")

if SAVED_FILE.exists():
    with SAVED_FILE.open() as file:
        LAST_ACTION = json.load(file)
else:
    LAST_ACTION = dict()


def sigterm_handler(signalnum, frame):
    """Save `LAST_ACCESS` before exit."""
    with SAVED_FILE.open("w") as file:
        json.dump(LAST_ACTION, file)
    exit(0)


# register SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)

app = Flask(__name__)


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


@app.route("/query/<user>")
def query(user):
    if _ := LAST_ACTION.get(user):
        action, time = _
        duration = datetime.now() - datetime.fromisoformat(time)
        return f"MAA last {action} {display(duration)}ago.\n"
    else:
        return "MAA has no action since the server started.\n"


@app.route("/report/<user>/<action>")
def report(user, action):
    if action not in ("online", "offline"):
        abort(404)
    LAST_ACTION[user] = (action, str(datetime.now()))
    return ""
