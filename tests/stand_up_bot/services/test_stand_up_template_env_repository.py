from stand_up_bot.services import StandUpTemplateEnvRepository


class TestStandUpTemplateEnvRepository:

    def test_find_all(self, monkeypatch):
        monkeypatch.setenv(
            "STAND_UP_TEMPLATES",
            " channel_a, 50 18 * * Mon-Fri;channel_b,50 9 * * Mon-Fri"
        )
        repository = StandUpTemplateEnvRepository()
        results = repository.find_all()
        template_a = results[0]
        template_b = results[1]

        assert template_a.channel == "channel_a"
        assert template_a.cron_expression == "50 18 * * Mon-Fri"
        assert "What did you do yesterday?" in template_a.questions
        assert "What are you going to do today?" in template_a.questions
        assert "Any blockers?" in template_a.questions

        assert template_b.channel == "channel_b"
        assert template_b.cron_expression == "50 9 * * Mon-Fri"
        assert "What did you do yesterday?" in template_b.questions
        assert "What are you going to do today?" in template_b.questions
        assert "Any blockers?" in template_b.questions

    def test_find_all_with_empty_default_channels(self, monkeypatch):
        monkeypatch.setenv("STAND_UP_TEMPLATES", "")
        repository = StandUpTemplateEnvRepository()
        results = repository.find_all()

        assert len(results) == 0

    def test_find_all_with_environment_variable_not_set(self, monkeypatch):
        monkeypatch.delenv("STAND_UP_TEMPLATES", raising=False)

        repository = StandUpTemplateEnvRepository()
        results = repository.find_all()

        assert len(results) == 0
