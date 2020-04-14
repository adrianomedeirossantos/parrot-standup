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

from stand_up import StandUp, StandUpService

r = redis.from_url(os.environ["REDIS_URL"])
# host='localhost', port=6379, db=0)

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ["SLACK_SIGNING_SECRET"], "/slack/events", app)
slack_web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
channel = "G011U6TETPV"
stand_up_service = StandUpService(slack_client=slack_web_client, redis=r)

@app.route('/stand_up')
def trigger_stand_up():
    response = slack_web_client.conversations_members(channel=channel)
    members = response.data['members']
    for m in members:
        stand_up = StandUp(user=m, channel=channel)
        stand_up_service.start(stand_up)

    return 'Stand up just started!'


@slack_events_adapter.on("message")
def message(payload):
    event = payload.get("event", {})

    if event["channel_type"] != "im":
        return

    user = event.get("user")
    if 'bot_profile' in event:
        return

    stand_up_service.on_update(user, event["text"])


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())

    scheduler = BackgroundScheduler()
    start_date = datetime(2020, 4, 12, 21, 55)
    scheduler.add_job(func=trigger_stand_up, trigger=IntervalTrigger(minutes=1, start_date=start_date))
    scheduler.start()
    app.run(host="0.0.0.0", port=os.environ["PORT"])
