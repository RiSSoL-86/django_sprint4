# Описание.

## Проект django_sprint4.

## Технологии:
* Python 3.7
* Django 3.2
* SQlite3

## Описание проекта

Доработка проекта django_sprint3.
Финальная версия небольшой социальной сети для публикации личных дневников.   

## Как запустить проект:

* Клонировать репозиторий и перейти в него в командной строке:

        git clone git@github.com:RiSSoL-86/django_sprint4.git
        cd django_sprint4

* Cоздать и активировать виртуальное окружение:

        python3 -m venv env
        source venv/Scripts/activate

* Установить зависимости из файла requirements.txt:

        python3 -m pip install --upgrade pip
        pip install -r requirements.txt

* Выполнить миграции:

        python3 manage.py migrate


* Запустить проект:

        python manage.py runserver

* Перейти на локальный сервер:

        http://127.0.0.1:8000/
