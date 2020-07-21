import os

from stand_up_bot.services import SalutationService


DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class TestSalutationService:

    greetings = [
        "Test 1! How are you?",
        "Test 2! How you doing?",
        "Test 3! How is it going?"
    ]

    farewells = [
        "Test 1! Good-bye!",
        "Test 2! See you soon!",
        "Test 3! See you later!"
    ]

    def test_say_hi_when_greetings_file_exists(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "greetings_test.csv"),
            os.path.join(DIR_PATH, "farewells_test.csv")
        )

        result = salutation_service.say_hi()

        assert result in self.greetings

    def test_say_hi_when_greetings_file_does_not_exist(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "does_not_exist.csv"),
            os.path.join(DIR_PATH, "farewells_test.csv")
        )

        result = salutation_service.say_hi()

        assert "Hello there! How you doing?" == result

    def test_say_hi_when_greetings_file_is_empty(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "empty_file.csv"),
            os.path.join(DIR_PATH, "farewells_test.csv")
        )

        result = salutation_service.say_hi()

        assert "Hello there! How you doing?" == result

    def test_say_good_bye_when_farewells_file_exists(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "greetings_test.csv"),
            os.path.join(DIR_PATH, "farewells_test.csv")
        )

        result = salutation_service.say_good_bye()

        assert result in self.farewells

    def test_say_good_bye_when_farewells_file_does_not_exist(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "does_not_exist.csv"),
            os.path.join(DIR_PATH, "does_not_exist.csv")
        )

        result = salutation_service.say_good_bye()

        assert "Good-bye!" == result

    def test_say_good_bye_when_farewells_file_is_empty(self):
        salutation_service = SalutationService(
            os.path.join(DIR_PATH, "greetings_test.csv"),
            os.path.join(DIR_PATH, "empty_file.csv")
        )

        result = salutation_service.say_good_bye()

        assert "Good-bye!" == result
