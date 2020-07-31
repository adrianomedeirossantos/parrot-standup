class StandUpTemplate:
    def __init__(self, channel, cron_expression, questions):
        self.channel = channel
        self.cron_expression = cron_expression
        self.questions = questions


class StandUp:
    def __init__(self, user, template):
        self.user = user
        self.template = template
        self.number_of_questions = len(self.template.questions)
        self.answered_questions = []
        self.answers = {}

    def has_started(self):
        return len(self.template.questions) == self.number_of_questions

    def has_pending_questions(self):
        return len(self.template.questions) > 0

    def next_question(self):
        next = self.template.questions.pop(0)
        self.answered_questions.append(next)
        return next
