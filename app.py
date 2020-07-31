import logging
import os
import redis
import ssl as ssl_lib

import certifi
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter

from stand_up_bot.services import (
    SalutationService,
    StandUpScheduler,
    StandUpService,
    StandUpTemplateEnvRepository
)

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

r = redis.from_url(os.environ["REDIS_URL"])

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(
    os.environ["SLACK_SIGNING_SECRET"], "/slack/events", app
)


@slack_events_adapter.on("message")
def message(payload):
    event = payload.get("event", {})

    if event["channel_type"] != "im":
        return

    user = event.get("user")
    if "bot_profile" in event:
        return

    if event.get("subtype") == "message_changed":
        stand_up_service.update_answer(
            event["message"]["user"],
            event["message"]["client_msg_id"],
            event["message"]["text"],
        )
    else:
        stand_up_service.store_answer(
            user,
            event["client_msg_id"],
            event["text"]
        )


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())

    slack_web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    salutation_service = SalutationService(
        greetings_file=os.path.join(DIR_PATH, "data/greetings.csv"),
        farewells_file=os.path.join(DIR_PATH, "data/fareweels.csv"),
    )
    stand_up_service = StandUpService(
        slack_client=slack_web_client,
        redis=r,
        salutation_service=salutation_service
    )
    stand_up_template_repository = StandUpTemplateEnvRepository()

    scheduler = StandUpScheduler(
        stand_up_service,
        stand_up_template_repository
    )

    scheduler.start()
    app.run(host="0.0.0.0", port=os.environ["PORT"])
