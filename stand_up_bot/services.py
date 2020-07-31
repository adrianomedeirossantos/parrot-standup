import abc
import csv
import os
import pickle
import random
import redis

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from slack import WebClient

from stand_up_bot.models import StandUp, StandUpTemplate


class SalutationService:
    def __init__(self, greetings_file, farewells_file):
        self.greetings = self.__load_messages(greetings_file)
        self.farewells = self.__load_messages(farewells_file)

    def say_hi(self):
        if not self.greetings:
            return "Hello there! How you doing?"

        return self.greetings[random.randint(0, len(self.greetings) - 1)]

    def say_good_bye(self):
        if not self.farewells:
            return "Good-bye!"

        return self.farewells[random.randint(0, len(self.farewells) - 1)]

    def __load_messages(self, filename):
        rows = []

        try:
            with open(filename) as csv_data_file:
                csv_reader = csv.reader(csv_data_file, delimiter="\n")
                for row in csv_reader:
                    rows.append(row[0])
        except OSError:
            return []

        return rows


class StandUpTemplateRepository:
    @abc.abstractmethod
    def find_all(self):
        pass


class StandUpTemplateEnvRepository(StandUpTemplateRepository):
    """
        A stand up template repository which loads templates from
        an environment variable. Each element contains the channel
        name and a cron expression separated by ',' and elements are
        separated by a ';'

        Eg. "channel_a,50 18 * * Mon-Fri;channel_b,50 18 * * Mon-Fri;"
    """
    def __init__(self, ):
        env_templates = os.getenv("STAND_UP_TEMPLATES")
        if env_templates:
            self.templates = [c.strip() for c in env_templates.split(';')]
        else:
            self.templates = []

        self.questions = [
            "What did you do yesterday?",
            "What are you going to do today?",
            "Any blockers?",
        ]

    def find_all(self):
        templates = []
        for t in self.templates:
            channel, cron_expression = [t.strip() for t in t.split(",")]
            template = StandUpTemplate(
                channel,
                cron_expression,
                self.questions
            )
            templates.append(template)

        return templates


class StandUpService:
    def __init__(
            self,
            slack_client: WebClient,
            redis: redis.Redis,
            salutation_service: SalutationService
    ):
        self.slack_client = slack_client
        self.redis = redis
        self.salutation_service = salutation_service

    def trigger(self, template):
        response = self.slack_client.conversations_members(
            channel=template.channel
        )
        members = response.data["members"]
        for m in members:
            stand_up = StandUp(user=m, template=template)
            self.start(stand_up)

    def start(self, stand_up):
        intro = "It's time for our *Standup*!"
        greetings = f"{self.salutation_service.say_hi()}\n{intro}"

        start_msg = f"{greetings}\n{stand_up.next_question()}"
        self.slack_client.chat_postMessage(
            channel=stand_up.user, text=start_msg,
        )

        pickled_object = pickle.dumps(stand_up)
        self.redis.set(stand_up.user, pickled_object)

        return

    def update_answer(self, user, message_id, answer):
        packed_stand_up = self.redis.get(user)

        if packed_stand_up is None:
            return

        stand_up = pickle.loads(packed_stand_up)
        stand_up.answers[message_id] = answer
        pickled_object = pickle.dumps(stand_up)
        self.redis.set(user, pickled_object)

    def store_answer(self, user, message_id, answer):
        packed_stand_up = self.redis.get(user)
        if packed_stand_up is None:
            return

        stand_up = pickle.loads(packed_stand_up)

        stand_up.answers[message_id] = answer

        if stand_up.has_pending_questions():
            self.slack_client.chat_postMessage(
                channel=stand_up.user, text=stand_up.next_question(),
            )
            pickled_object = pickle.dumps(stand_up)
            self.redis.set(stand_up.user, pickled_object)
        else:
            self.slack_client.chat_postMessage(
                channel=stand_up.user,
                text=self.salutation_service.say_good_bye(),
            )

            self._send_summary(stand_up)
            self.redis.delete(stand_up.user)

    def _send_summary(self, stand_up):
        q = list(map(lambda x: f"*{x}*", stand_up.answered_questions))
        a = list(map(lambda x: f"{x}", stand_up.answers.values()))

        user_info = self.slack_client.users_info(user=stand_up.user)
        result = [val for pair in zip(q, a) for val in pair]
        result = "\n".join(result)
        self.slack_client.chat_postMessage(
            channel=stand_up.template.channel,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f'*{user_info["user"]["name"]}*\'s update',
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": result}
                    ]
                },
            ],
        )


class StandUpScheduler:
    def __init__(
            self,
            stand_up_service: StandUpService,
            stand_up_template_repository: StandUpTemplateRepository
    ):
        self.stand_up_service = stand_up_service
        self.stand_up_template_repository = stand_up_template_repository
        self.scheduler = BackgroundScheduler()

    def start(self):
        templates = self.stand_up_template_repository.find_all()
        for t in templates:
            cron_trigger = CronTrigger.from_crontab(t.cron_expression)
            self.scheduler.add_job(
                func=self.stand_up_service.trigger,
                trigger=cron_trigger,
                args=[t]
            )

        self.scheduler.start()
