import datetime
import random
import re
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Tuple, Type, List

import django.test.client
import pytest
import pytz
from django.db.models import Model, ImageField
from django.forms import BaseForm
from django.http import HttpResponse
from django.utils import timezone

from blog.models import Post
from conftest import (
    _TestModelAttrs, KeyVal, get_create_a_post_get_response_safely)
from adapters.post import PostModelAdapter
from fixtures.types import CommentModelAdapterT, ModelAdapterT
from form.base_form_tester import FormValidationException
from form.post.create_form_tester import CreatePostFormTester
from form.post.delete_tester import DeletePostTester
from form.post.edit_form_tester import EditPostFormTester
from form.post.find_urls import find_edit_and_delete_urls
from form.post.form_tester import PostFormTester
from test_edit import _test_edit


@pytest.mark.parametrize(('field', 'type', 'params'), [
    ('image', ImageField, {}),
])
class TestPostModelAttrs(_TestModelAttrs):

    @pytest.fixture(autouse=True)
    def _set_model(self):
        self._model = PostModelAdapter(Post)

    @property
    def model(self):
        return self._model


@pytest.mark.django_db(transaction=True)
def test_post_created_at(post_with_published_location):
    now = timezone.now()
    now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)
    assert abs(
        post_with_published_location.created_at.replace(tzinfo=None) - now_utc
    ) < datetime.timedelta(seconds=1), (
        'Убедитесь, что при создании публикации ей присваиваются '
        'текущие дата и время.'
    )


@pytest.mark.django_db(transaction=True)
def test_post(
        published_category: Model,
        published_location: Model,
        user_client: django.test.Client,
        another_user_client: django.test.Client,
        unlogged_client: django.test.Client,
        comment_to_a_post: Model,
        create_post_context_form_item: Tuple[str, BaseForm],
        PostModel: Type[Model],
        CommentModelAdapter: CommentModelAdapterT
):
    _, ctx_form = create_post_context_form_item

    create_a_post_get_response = get_create_a_post_get_response_safely(
        user_client)

    response_on_created, created_items = _test_create_items(
        PostModel, PostModelAdapter,
        another_user_client,
        create_a_post_get_response, ctx_form,
        published_category, published_location,
        unlogged_client, user_client)

    edit_response, edit_url, del_url = _test_edit_post(
        CommentModelAdapter, another_user_client, comment_to_a_post,
        unlogged_client=unlogged_client, user_client=user_client)

    item_to_delete_adapter = PostModelAdapter(
        CommentModelAdapter(comment_to_a_post).post)
    del_url_addr = del_url.key

    DeletePostTester(
        item_to_delete_adapter.item_cls,
        user_client, another_user_client, unlogged_client,
        item_adapter=item_to_delete_adapter).test_delete_item(
        qs=item_to_delete_adapter.item_cls.objects.all(),
        delete_url_addr=del_url_addr)

    response = user_client.get(edit_url)
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        'Убедитесь, что при обращении к странице редактирования '
        'несуществующей публикации возвращается статус 404.')

    response = user_client.get(del_url_addr)
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        'Убедитесь, что при обращении к странице удаления '
        'несуществующей публикации возвращается статус 404.')


def _test_create_items(
        PostModel, PostAdapter, another_user_client,
        create_a_post_get_response, ctx_form,
        published_category, published_location, unlogged_client,
        user_client) -> Tuple[HttpResponse, List[ModelAdapterT]]:
    creation_tester = CreatePostFormTester(
        create_a_post_get_response, PostModel, user_client,
        another_user_client, unlogged_client,
        ModelAdapter=PostAdapter, item_adapter=None)
    Form: Type[BaseForm] = type(ctx_form)
    item_ix_start: int = random.randint(1000000, 2000000)
    item_ix_cnt: int = 5
    rand_range = list(range(item_ix_start, item_ix_start + item_ix_cnt))
    forms_data = []
    for i in rand_range:
        forms_data.append({
            'title': f'Test create post {i} title',
            'text': f'Test create post {i} text',
            'pub_date': datetime.datetime.now(),
            'category': published_category,
            'location': published_location
        })
    forms_to_create = creation_tester.init_create_item_forms(
        Form, Model=PostModel, ModelAdapter=PostAdapter,
        forms_unadapted_data=forms_data
    )
    try:
        creation_tester.test_unlogged_cannot_create(
            form=forms_to_create[0], qs=PostModel.objects.all())
    except FormValidationException as e:
        raise AssertionError(
            f'Убедитесь, что для валидации {creation_tester.of_which_form} '
            'достаточно заполнить следующие поля: '
            f'{list(forms_to_create[0].data.keys())}. '
            f'При валидации формы возникли следующие ошибки: {e}'
        )
    response_on_created, created_items = creation_tester.test_create_several(
        forms=forms_to_create[1:], qs=PostModel.objects.all())
    content = response_on_created.content.decode(encoding='utf8')
    creation_tester.test_creation_response(content, created_items)
    return response_on_created, created_items


def _test_edit_post(
        CommentModelAdapter, another_user_client, comment_to_a_post,
        unlogged_client, user_client) -> Tuple[HTTPResponse, str, str]:
    comment_adapter = CommentModelAdapter(comment_to_a_post)
    item_to_edit = comment_adapter.post
    post_adapter = PostModelAdapter(item_to_edit)
    post_url = f'/posts/{item_to_edit.id}/'
    response_on_commented = user_client.get(post_url)
    edit_url, del_url = find_edit_and_delete_urls(
        post_adapter,
        comment_adapter,
        response_on_commented,
        urls_start_with=KeyVal(
            key=post_url.replace(
                f'/{item_to_edit.id}/',
                '/<post_id>/'
            ),
            val=post_url
        ))
    assert edit_url.key == f'/posts/{item_to_edit.id}/edit/', (
        'Убедитесь, что страница редактирования публикации имеет '
        'адрес posts/<post_id>/edit/.'
    )
    edit_url = KeyVal(
        re.sub(r'\d+', str(item_to_edit.id), edit_url.key), edit_url.val)
    image = PostFormTester.generate_files_dict()
    item_to_edit_adapter = PostModelAdapter(item_to_edit)
    old_prop_value = item_to_edit_adapter.displayed_field_name_or_value
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value:
            f'{old_prop_value} edited'
    }
    edit_response = _test_edit(
        edit_url, PostModelAdapter, item_to_edit,
        EditFormTester=EditPostFormTester,
        user_client=user_client, another_user_client=another_user_client,
        unlogged_client=unlogged_client, file_data=image, **update_props)
    return edit_response, edit_url, del_url
