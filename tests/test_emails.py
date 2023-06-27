from django.conf import settings
from django.core.mail.backends.locmem import EmailBackend


def test_gitignore():
    try:
        with open(settings.BASE_DIR / '..' / '.gitignore', 'r',
                  encoding='utf-8', errors='ignore') as fh:
            gitignore = fh.read()
    except Exception as e:
        raise AssertionError(
            'При чтении файла `.gitignore` в корне проекта возникла ошибка:\n'
            f'{type(e).__name__}: {e}'
        )
    assert 'sent_emails/' in gitignore, (
        'Убедитесь, что в файле `.gitignore` в корне проекта указана '
        'директория `sent_emails/` для подключения файлового бэкенда '
        'отправки e-mail сообщений.'
    )


def test_email_backend_settings():
    assert hasattr(settings, 'EMAIL_BACKEND'), (
        'Убедитесь, что в настроек проекта задана настройка `EMAIL_BACKEND`.'
    )
    assert EmailBackend.__module__ in settings.EMAIL_BACKEND, (
        'Убедитесь, что с помощью настроки `EMAIL_BACKEND` подключен '
        'файловый бэкенд для отправки e-mail.'
    )
    excpect_email_file = settings.BASE_DIR / 'sent_emails'
    assert getattr(settings, 'EMAIL_FILE_PATH', '') == excpect_email_file, (
        'Убедитесь, что с помощью настроки `EMAIL_FILE_PATH` для '
        'отправки e-mail задан файл `BASE_DIR / \'sent_emails\'`.'
    )
