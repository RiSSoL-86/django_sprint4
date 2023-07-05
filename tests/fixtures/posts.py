from datetime import datetime, timedelta
from typing import Tuple

import pytest
import pytz
from django.db.models import Model
from django.forms import BaseForm
from django.test import Client
from mixer.backend.django import Mixer

from conftest import (
    N_PER_FIXTURE,
    N_PER_PAGE,
    KeyVal,
    get_a_post_get_response_safely,
    get_create_a_post_get_response_safely,
    _testget_context_item_by_class,
)


@pytest.fixture
def posts_with_unpublished_category(mixer: Mixer, user: Model):
    return mixer.cycle(N_PER_FIXTURE).blend(
        "blog.Post", author=user, category__is_published=False
    )


@pytest.fixture
def future_posts(mixer: Mixer, user: Model):
    date_later_now = (
        datetime.now(tz=pytz.UTC) + timedelta(days=date)
        for date in range(1, 11)
    )
    return mixer.cycle(N_PER_FIXTURE).blend(
        "blog.Post", author=user, pub_date=date_later_now
    )


@pytest.fixture
def unpublished_posts_with_published_locations(
    mixer: Mixer, user, published_locations, published_category
):
    return mixer.cycle(N_PER_FIXTURE).blend(
        "blog.Post",
        author=user,
        is_published=False,
        category=published_category,
        location=mixer.sequence(*published_locations),
    )


@pytest.fixture
def post_with_another_category(
    mixer: Mixer, user, published_location, published_category,
        another_category
):
    assert published_category.id != another_category.id
    return mixer.blend(
        "blog.Post",
        location=published_location,
        category=another_category,
        author=user,
    )


@pytest.fixture
def post_of_another_author(
    mixer: Mixer, user, another_user,  published_location, published_category
):
    assert user.id != another_user.id
    return mixer.blend(
        "blog.Post",
        location=published_location,
        category=published_category,
        author=another_user,
    )


@pytest.fixture
def post_with_published_location(
    mixer: Mixer, user, published_location, published_category
):
    return mixer.blend(
        "blog.Post",
        location=published_location,
        category=published_category,
        author=user,
    )


@pytest.fixture
def many_posts_with_published_locations(
    mixer: Mixer, user, published_locations, published_category
):
    return mixer.cycle(N_PER_PAGE * 2).blend(
        "blog.Post",
        author=user,
        category=published_category,
        location=mixer.sequence(*published_locations),
    )


@pytest.fixture
def post_comment_context_form_item(
    user_client: Client, post_with_published_location
) -> Tuple[str, BaseForm]:
    response = get_a_post_get_response_safely(
        user_client, post_with_published_location.id
    )
    result: KeyVal = _testget_context_item_by_class(
        response.context,
        BaseForm,
        (
            "Убедитесь, что в словарь контекста для страницы поста передаётся"
            " ровно одна форма для создания комментария."
        ),
    )
    return result


@pytest.fixture
def create_post_context_form_item(
    user_client: Client, post_with_published_location
) -> Tuple[str, BaseForm]:
    response = get_create_a_post_get_response_safely(user_client)
    result: KeyVal = _testget_context_item_by_class(
        response.context,
        BaseForm,
        (
            "Убедитесь, что в словарь контекста для страницы создания поста"
            " передаётся ровно одна форма."
        ),
    )
    return result
