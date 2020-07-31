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
