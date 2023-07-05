from django.conf import settings
from django.core.mail.backends.locmem import EmailBackend


def test_gitignore():
    try:
        with open(
            settings.BASE_DIR / ".." / ".gitignore",
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as fh:
            gitignore = fh.read()
    except Exception as e:
        raise AssertionError(
            "При чтении файла `.gitignore` в корне проекта возникла ошибка:\n"
            f"{type(e).__name__}: {e}"
        )
    assert "sent_emails/" in gitignore, (
        "Убедитесь, что директория `sent_emails/`, служащая для хранения"
        " e-mail сообщений, указана в файле `.gitignore` в корне проекта."
    )


def test_email_backend_settings():
    assert hasattr(
        settings, "EMAIL_BACKEND"
    ), "Убедитесь, что в проекте задана настройка `EMAIL_BACKEND`."
    assert EmailBackend.__module__ in settings.EMAIL_BACKEND, (
        "Убедитесь, что файловый бэкенд для отправки e-mail подключен с"
        " помощью настройки `EMAIL_BACKEND`."
    )
    excpect_email_file = settings.BASE_DIR / "sent_emails"
    assert getattr(settings, "EMAIL_FILE_PATH", "") == excpect_email_file, (
        "Убедитесь, что в настройке `EMAIL_FILE_PATH` указан путь `BASE_DIR /"
        " 'sent_emails'`."
    )
