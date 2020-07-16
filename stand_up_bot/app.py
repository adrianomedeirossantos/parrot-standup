from datetime import datetime
import logging
import os
import redis
import ssl as ssl_lib

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import certifi
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter

from models import StandUp
from services import SalutationService, StandUpService

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

r = redis.from_url(os.environ["REDIS_URL"])

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(
    os.environ["SLACK_SIGNING_SECRET"], "/slack/events", app
)
slack_web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
# channel = "G011U6TETPV" - Alex test channel
# channel = "G0124A0PZ09" - pricing old standup
network_engineering_channel = "G014NBSPUP8"
channel = os.getenv("STAND_UP_CHANNEL", network_engineering_channel)
salutation_service = SalutationService(
    greetings_file=os.path.join(DIR_PATH, "data/greetings.csv"),
    farewells_file=os.path.join(DIR_PATH, "data/fareweels.csv"),
)
stand_up_service = StandUpService(slack_client=slack_web_client, redis=r, salutation_service=salutation_service)


@app.route("/stand_up")
def trigger_stand_up():
    weekday = datetime.today().weekday()
    if weekday >= 5:
        return "Skipping standup as it's weekend"

    response = slack_web_client.conversations_members(channel=channel)
    members = response.data["members"]
    for m in members:
        stand_up = StandUp(user=m, channel=channel)
        stand_up_service.start(stand_up)

    return "Stand up just started!"


@slack_events_adapter.on("message")
def message(payload):
    event = payload.get("event", {})

    if event["channel_type"] != "im":
        return

    user = event.get("user")
    if "bot_profile" in event:
        return

    if event.get("subtype") is not None and event["subtype"] == "message_changed":
        stand_up_service.update_answer(
            event["message"]["user"],
            event["message"]["client_msg_id"],
            event["message"]["text"],
        )
    else:
        stand_up_service.store_answer(user, event["client_msg_id"], event["text"])


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())

    scheduler = BackgroundScheduler()
    start_date = datetime(2020, 6, 5, 8, 50)
    scheduler.add_job(
        func=trigger_stand_up, trigger=IntervalTrigger(days=1, start_date=start_date)
    )
    scheduler.start()
    app.run(host="0.0.0.0", port=os.environ["PORT"])
