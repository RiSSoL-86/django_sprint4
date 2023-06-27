import datetime
import random
from http import HTTPStatus
from typing import Tuple, Any, Type

import django.test.client
import pytest
import pytz
from django.db.models import TextField, DateTimeField, ForeignKey, Model
from django.forms import BaseForm
from django.utils import timezone

from conftest import _TestModelAttrs, KeyVal, get_a_post_get_response_safely
from fixtures.types import CommentModelAdapterT
from form.base_form_tester import FormValidationException
from form.comment.create_form_tester import CreateCommentFormTester
from form.comment.delete_tester import DeleteCommentTester
from form.comment.edit_form_tester import EditCommentFormTester
from form.comment.find_urls import find_edit_and_delete_urls
from test_edit import _test_edit


@pytest.mark.usefixtures('CommentModel', 'CommentModelAdapter')
@pytest.mark.parametrize(('field', 'type', 'params'), [
    ('post', ForeignKey, {}),
    ('author', ForeignKey, {}),
    ('text', TextField, {}),
    ('created_at', DateTimeField, {'auto_now_add': True}),
])
class TestCommentModelAttrs(_TestModelAttrs):

    @pytest.fixture(autouse=True)
    def _set_model(self, CommentModel, CommentModelAdapter):
        self._model = CommentModelAdapter(CommentModel)

    @property
    def model(self):
        return self._model


@pytest.mark.django_db(transaction=True)
def test_comment_created_at(comment, CommentModelAdapter):
    now = timezone.now()
    now_utc = now.astimezone(pytz.UTC).replace(tzinfo=None)
    assert abs(
        comment.created_at.replace(tzinfo=None) - now_utc
    ) < datetime.timedelta(seconds=1), (
        'Убедитесь, что при создании комментария ему присваиваются '
        'текущие дата и время.'
    )


@pytest.mark.django_db(transaction=True)
def test_comment(
        user_client: django.test.Client,
        another_user_client: django.test.Client,
        unlogged_client: django.test.Client,
        post_with_published_location: Any,
        another_user: Model,
        post_comment_context_form_item: Tuple[str, BaseForm],
        CommentModel: Type[Model],
        CommentModelAdapter: CommentModelAdapterT):
    post_with_published_location.author = another_user
    post_with_published_location.save()
    _, ctx_form = post_comment_context_form_item
    a_post_get_response = get_a_post_get_response_safely(
        user_client, post_with_published_location.id)

    # create comments
    creation_tester = CreateCommentFormTester(
        a_post_get_response, CommentModel, user_client,
        another_user_client, unlogged_client, item_adapter=None,
        ModelAdapter=CommentModelAdapter)

    Form: Type[BaseForm] = type(ctx_form)

    item_ix_start: int = random.randint(1000000, 2000000)
    item_ix_cnt: int = 5
    rand_range = list(range(item_ix_start, item_ix_start + item_ix_cnt))
    forms_data = []
    for i in rand_range:
        forms_data.append({'text': f'Test create comment {i} text'})

    forms_to_create = creation_tester.init_create_item_forms(
        Form, Model=CommentModel, ModelAdapter=CommentModelAdapter,
        forms_unadapted_data=forms_data
    )
    try:
        creation_tester.test_unlogged_cannot_create(
            form=forms_to_create[0], qs=CommentModel.objects.all())
    except FormValidationException as e:
        raise AssertionError(
            f'Убедитесь, что для валидации {creation_tester.of_which_form} '
            'достаточно заполнить следующие поля: '
            f'{list(forms_to_create[0].data.keys())}. '
            f'При валидации формы возникли следующие ошибки: {e}'
        )

    response_on_created, created_items = creation_tester.test_create_several(
        forms_to_create[1:], qs=CommentModel.objects.all())
    content = response_on_created.content.decode(encoding='utf8')
    creation_tester.test_creation_response(content, created_items)

    index_content = user_client.get('/').content.decode('utf-8')
    if f'({len(created_items)})' not in index_content:
        raise AssertionError(
            'Убедитесь, что у публикаций на главной странице '
            'отображается количество комментариев. '
            'Оно должно быть указано в круглых скобках.'
        )

    created_item_adapters = [CommentModelAdapter(i) for i in created_items]

    # edit comments
    post_url = f'/posts/{post_with_published_location.id}/'
    edit_url, del_url = find_edit_and_delete_urls(
        created_item_adapters, response_on_created,
        urls_start_with=KeyVal(
            key=post_url.replace(
                f'/{post_with_published_location.id}/',
                '/<post_id>/'
            ),
            val=post_url
        ), user_client=user_client)

    item_to_edit = created_items[0]
    item_to_edit_adapter = CommentModelAdapter(item_to_edit)
    old_prop_value = item_to_edit_adapter.displayed_field_name_or_value
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value:
            f'{old_prop_value} edited'}
    delete_url_addr = del_url.key

    _test_edit(
        edit_url, CommentModelAdapter, item_to_edit,
        EditFormTester=EditCommentFormTester,
        user_client=user_client, another_user_client=another_user_client,
        unlogged_client=unlogged_client, **update_props
    )

    item_to_delete_adapter = item_to_edit_adapter
    DeleteCommentTester(
        item_to_delete_adapter.item_cls,
        user_client, another_user_client, unlogged_client,
        item_adapter=item_to_delete_adapter).test_delete_item(
        qs=item_to_delete_adapter.item_cls.objects.all(),
        delete_url_addr=delete_url_addr)

    response = user_client.get(edit_url)
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        'Убедитесь, что при обращении к странице редактирования '
        'несуществующего комментария возвращается статус 404.')

    response = user_client.get(delete_url_addr)
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        'Убедитесь, что при обращении к странице удаления '
        'несуществующего комментария возвращается статус 404.')
