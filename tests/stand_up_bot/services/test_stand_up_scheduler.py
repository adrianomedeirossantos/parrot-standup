from unittest.mock import patch
from stand_up_bot.models import StandUpTemplate
from stand_up_bot.services import StandUpScheduler


class TestStandUpScheduler:

    @patch("stand_up_bot.services.StandUpTemplateRepository")
    @patch("stand_up_bot.services.StandUpService")
    @patch("stand_up_bot.services.BackgroundScheduler")
    @patch("stand_up_bot.services.CronTrigger")
    @patch("apscheduler.schedulers.background.BaseScheduler")
    def test_start_scheduler(
            self,
            _base_scheduler_mock,
            cron_trigger_mock,
            background_scheduler_mock,
            stand_up_service_mock,
            stand_up_template_repository
    ):
        scheduler = background_scheduler_mock
        background_scheduler_mock.return_value = scheduler

        cron_trigger = cron_trigger_mock
        cron_trigger_mock.from_crontab.return_value = cron_trigger

        questions = [
            "What did you do yesterday?",
            "What are you going to do today?",
            "Any blockers?",
        ]
        template = StandUpTemplate("channel_a", "50 18 * * Mon-Fri", questions)
        templates = [template]

        stand_up_template_repository.find_all.return_value = templates

        stand_up_scheduler = StandUpScheduler(
            stand_up_service_mock,
            stand_up_template_repository
        )

        stand_up_scheduler.start()

        stand_up_template_repository.find_all.assert_called_once()
        scheduler.add_job.assert_called_once_with(
            func=stand_up_service_mock.trigger,
            trigger=cron_trigger,
            args=[template],
        )
        scheduler.start.assert_called_once()

    @patch("stand_up_bot.services.BackgroundScheduler")
    @patch("apscheduler.schedulers.background.BaseScheduler")
    @patch("stand_up_bot.services.StandUpService")
    @patch("stand_up_bot.services.StandUpTemplateRepository")
    def test_start_scheduler_with_no_templates(
            self,
            stand_up_template_repository,
            stand_up_service_mock,
            _base_scheduler_mock,
            background_scheduler_mock
    ):
        scheduler = background_scheduler_mock
        background_scheduler_mock.return_value = scheduler

        stand_up_template_repository.find_all.return_value = []

        stand_up_scheduler = StandUpScheduler(
            stand_up_service_mock,
            stand_up_template_repository
        )

        stand_up_scheduler.start()

        stand_up_template_repository.find_all.assert_called_once()
        scheduler.add_job.assert_not_called()
        scheduler.start.assert_called_once()
