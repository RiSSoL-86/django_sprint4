{% extends "base.html" %}
{% load django_bootstrap5 %}
{% block content %}
  {% if next %}
    {% if user.is_authenticated %}
      <p class="text-center">
        У вашего аккаунта нет доступа к этой странице.
        Чтобы продолжить, войдите в систему с аккаунтом,
        у которого есть доступ.
      </p>
    {% else %}
      <p class="text-center">
        Пожалуйста, войдите в систему,
        чтобы просматривать эту страницу.
      </p>
    {% endif %}
  {% endif %}
  <div class="col d-flex justify-content-center">
    <div class="card" style="width: 40rem;">
      <div class="card-header">
        Войти в систему
      </div>
      <div class="card-body">
        <form method="post" action="{% url 'login' %}">
          {% csrf_token %}
          {% bootstrap_form form %}
          <input type="hidden" name="next" value="{{ next }}">
          {% bootstrap_button button_type="submit" content="Войти" %}
        </form>
        <div>
          <a href="{% url 'password_reset' %}">Забыли пароль?</a>
        </div>
      </div>
    </div>
  </div>
{% endblock %}