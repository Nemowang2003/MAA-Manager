from flask import Flask, abort
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from sys import stderr
import traceback
import json
import signal
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage
import requests
import time
import hmac
import hashlib
from apscheduler.schedulers.background import BackgroundScheduler
from random import randint

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
        self._msg["Subject"] = "MAA-Manager Offline Notice"
        self._msg.set_content(self.OFFLINE.format(user))
        with self.smtp_server() as smtp_server:
            smtp_server.send_message(self._msg)

    def send_daily_error(self, user: str):
        self._msg["Subject"] = "MAA-Manager Daily-Sign Error"
        self._msg.set_content(self.DAILY_ERROR.format(user))
        with self.smtp_server() as smtp_server:
            smtp_server.send_message(self._msg)


class DailySignException(Exception):
    pass


@dataclass
class DailySign:
    phone: str
    password: str
    uid: str

    HEADER = {
        "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
        "Accept-Encoding": "gzip",
        "Connection": "close",
    }

    LOGIN_URL = "https://as.hypergryph.com/user/auth/v1/token_by_phone_password"
    GRANT_URL = "https://as.hypergryph.com/user/oauth2/v2/grant"
    CRED_URL = "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code"
    DAILY_URL = "https://zonai.skland.com/api/v1/game/attendance"

    def __post_init__(self):
        try:
            hypergryph_token = requests.post(
                self.LOGIN_URL,
                json={
                    "phone": self.phone,
                    "password": self.password,
                },
                headers=self.HEADER,
            ).json()["data"]["token"]
        except Exception as e:
            raise DailySignException(
                f"[{self.phone}]: Failed to get token of `ak.hypergryph.com`."
            ) from e

        try:
            grant_code = requests.post(
                self.GRANT_URL,
                json={
                    "appCode": "4ca99fa6b56cc2ba",
                    "token": hypergryph_token,
                    "type": 0,
                },
                headers=self.HEADER,
            ).json()["data"]["code"]
            _ = requests.post(
                self.CRED_URL,
                json={
                    "kind": 1,
                    "code": grant_code,
                },
                headers=self.HEADER,
            ).json()["data"]
            self.skland_cred = _["cred"]
            self.skland_token = _["token"]
        except Exception as e:
            raise DailySignException(
                f"[{self.phone}]: Failed to log into `skland.com`."
            ) from e

    def __call__(self):
        print(f"==========DailySign [{self.phone}] Started==========", file=stderr)
        try:
            # It was said that `- 2` should be added according to experience.
            timestamp = str(time.time() - 2)
            # It was said that it's fine for all fields (other than timestamp) to be empty.
            header = {
                "platform": "",
                "dId": "",
                "vName": "",
                "timestamp": timestamp,
            }
            payload = {
                "uid": self.uid,
                "gameId": 1,
            }
            content = "".join(
                [self.DAILY_URL, timestamp, json.dumps(header, separators=(",", ":"))]
            )
            encrypted = (
                hmac.new(self.skland_token.encode(), content.encode(), hashlib.sha256)
                .hexdigest()
                .encode()
            )

            # It was said that the signature is needed, but it still worked without it.
            # So I left it `assigned but never used`, intentionally (for future use).
            signature = hashlib.md5(encrypted).hexdigest()

            awards = requests.post(
                self.DAILY_URL,
                json=payload,
                headers={"cred": self.skland_cred, "sign": signature}
                | self.HEADER
                | header,
            ).json()["data"]["awards"]

            for award in awards:
                print(
                    f"Award: {award['resource']['name']} × {award.get('count', 1)}",
                    file=stderr,
                )

        except Exception:
            MAIL_SENDER.send_daily_error(self.phone)
            print("==========DailySign Sign Failed==========", file=stderr)
            traceback.print_exc()
            print("==========DailySign Sign Failed==========", file=stderr)

        finally:
            print(f"==========DailySign [{self.phone}] Ended==========", file=stderr)


CONFIG = Path("config/config.json")

MAIL_SENDER: MailSender | None

if CONFIG.exists():
    try:
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

            SCHEDULER = BackgroundScheduler()
            for daily_config in config.get("daily-sign", []):
                try:
                    daily_sign = DailySign(
                        phone=daily_config["phone"],
                        password=daily_config["password"],
                        uid=daily_config["uid"],
                    )

                    hour = randint(0, 8)
                    minute = randint(0, 59)
                    second = randint(0, 59)
                    print(
                        f"[{daily_sign.phone}]: Schedule daily sign at {hour:02}:{minute:02}:{second:02}.",
                        file=stderr,
                    )
                    SCHEDULER.add_job(
                        daily_sign,
                        trigger="cron",
                        hour=hour,
                        minute=minute,
                        second=second,
                    )

                except DailySignException:  # error with DailySign auth
                    print("==========DailySign Auth Failed==========", file=stderr)
                    traceback.print_exc()
                    print("==========DailySign Auth Failed==========", file=stderr)

            if SCHEDULER.get_jobs():
                SCHEDULER.start()

    except Exception:  # other fatal error
        MAIL_SENDER = None
        print("==========ERROR READING CONFIG==========", file=stderr)
        traceback.print_exc()
        print("==========ERROR READING CONFIG==========", file=stderr)

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
