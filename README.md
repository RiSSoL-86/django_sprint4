# Описание.

## Проект django_sprint4.

## Технологии:
* Python 3.7
* Django 3.2
* SQlite3

## Описание проекта

Доработка проекта django_sprint3.
Финальная версия небольшой социальной сети для публикации личных дневников. 
![image](https://github.com/RiSSoL-86/django_sprint4/assets/110422516/b744dfec-ac8a-4f60-9428-a8ce106f41b5)


## Как запустить проект:

* Клонировать репозиторий и перейти в него в командной строке:

        git clone git@github.com:RiSSoL-86/django_sprint4.git
        cd django_sprint4

* Cоздать и активировать виртуальное окружение:

        python -m venv venv
        source venv/Scripts/activate

* Установить зависимости из файла requirements.txt:

        python -m pip install --upgrade pip
        pip install -r requirements.txt

* Выполнить миграции:

        python manage.py migrate


* Запустить проект:

        python manage.py runserver

* Перейти на локальный сервер:

        http://127.0.0.1:8000/
