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
