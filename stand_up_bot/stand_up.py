import csv
import os
import pickle
import random
import redis

from slack import WebClient


class StandUp:
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        self.questions = [
            "What did you do yesterday?",
            "What are you going to do today?",
            "Any blockers?",
        ]
        self.number_of_questions = len(self.questions)
        self.answered_questions = []
        self.answers = {}

    def has_started(self):
        return len(self.questions) == self.number_of_questions

    def has_pending_questions(self):
        return len(self.questions) > 0

    def next_question(self):
        next = self.questions.pop(0)
        self.answered_questions.append(next)
        return next


class StandUpService:
    def __init__(self, slack_client: WebClient, redis: redis.Redis):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.slack_client = slack_client
        self.redis = redis
        self.greetings = self._load_messages(os.path.join(dir_path, "greetings.csv"))
        self.good_bye = self._load_messages(os.path.join(dir_path, "good_bye.csv"))

    def start(self, stand_up):
        greetings = self._greetings()

        self.slack_client.chat_postMessage(
            channel=stand_up.user, text=f"{greetings}\n{stand_up.next_question()}",
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
                channel=stand_up.user, text=self._good_bye(),
            )

            self._send_summary(stand_up)
            self.redis.delete(stand_up.user)

    def _greetings(self):
        message = self.greetings[random.randint(0, len(self.greetings) - 1)]
        return f"{message}\nIt's time for our *Standup*!"

    def _send_summary(self, stand_up):
        q = list(map(lambda x: f"*{x}*", stand_up.answered_questions))
        a = list(map(lambda x: f"{x}", stand_up.answers.values()))

        user_info = self.slack_client.users_info(user=stand_up.user)
        result = [val for pair in zip(q, a) for val in pair]
        result = "\n".join(result)
        self.slack_client.chat_postMessage(
            channel=stand_up.channel,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f'*{user_info["user"]["name"]}*\'s update',
                    },
                },
                {"type": "context", "elements": [{"type": "mrkdwn", "text": result}]},
            ],
        )

    def _good_bye(self):
        message = self.good_bye[random.randint(0, len(self.good_bye) - 1)]
        return f"{message}\n I have to go to the beach now :beach_with_umbrella:!"

    def _load_messages(self, filename):
        rows = []

        with open(filename) as csvDataFile:
            csvReader = csv.reader(csvDataFile, delimiter="\n")
            for row in csvReader:
                rows.append(row[0])

        return rows
