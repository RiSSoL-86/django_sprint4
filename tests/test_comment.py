import datetime
import random
from http import HTTPStatus
from typing import Tuple, Any, Type, List, Union

import django.test.client
import pytest
import pytz
from django.db.models import TextField, DateTimeField, ForeignKey, Model
from django.forms import BaseForm
from django.utils import timezone

from adapters.post import PostModelAdapter
from conftest import _TestModelAttrs, KeyVal, get_a_post_get_response_safely
from fixtures.types import CommentModelAdapterT
from form.base_form_tester import (
    FormValidationException, AuthorisedSubmitTester)
from form.comment.create_form_tester import CreateCommentFormTester
from form.comment.delete_tester import DeleteCommentTester
from form.comment.edit_form_tester import EditCommentFormTester
from form.comment.find_urls import find_edit_and_delete_urls
from test_content import ProfilePostContentTester, profile_content_tester
from test_edit import _test_edit


@pytest.mark.usefixtures("CommentModel", "CommentModelAdapter")
@pytest.mark.parametrize(
    ("field", "type", "params", "field_error", "type_error",
     "param_error", "value_error"),
    [
        ("post", ForeignKey, {}, None, None, None, None),
        ("author", ForeignKey, {}, None, None, None, None),
        ("text", TextField, {}, None, None, None, None),
        ("created_at", DateTimeField, {"auto_now_add": True},
         None, None, None, None),
    ],
    ids=["`post` field", "`author` field",
         "`text` field", "`created_at` field"]
)
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
        "Убедитесь, что при создании комментария ему присваиваются текущие"
        " дата и время."
    )


def create_comment_creation_forms(
        creation_tester: CreateCommentFormTester,
        Form: Type[BaseForm],
        CommentModel: Type[Model],
        CommentModelAdapter: CommentModelAdapterT,
        return_single_form: bool = False,
) -> Union[BaseForm, List[BaseForm]]:
    item_ix_start: int = random.randint(1000000, 2000000)
    item_ix_cnt: int = 5
    rand_range = list(range(item_ix_start, item_ix_start + item_ix_cnt))
    forms_data = []
    for i in rand_range:
        forms_data.append({"text": f"Test create comment {i} text"})

    forms_to_create = creation_tester.init_create_item_forms(
        Form,
        Model=CommentModel,
        ModelAdapter=CommentModelAdapter,
        forms_unadapted_data=forms_data,
    )

    try:
        creation_tester.test_unlogged_cannot_create(
            form=forms_to_create[0], qs=CommentModel.objects.all()
        )
    except FormValidationException as e:
        raise AssertionError(
            "Убедитесь, что для валидации"
            f" {creation_tester.of_which_form} достаточно заполнить следующие"
            f" поля: {list(forms_to_create[0].data.keys())}. При валидации"
            f" формы возникли следующие ошибки: {e}"
        )

    if return_single_form:
        return forms_to_create[0]
    else:
        return forms_to_create


@pytest.mark.django_db(transaction=True)
def test_comment(
        user_client: django.test.Client,
        another_user_client: django.test.Client,
        unlogged_client: django.test.Client,
        post_with_published_location: Any,
        another_user: Model,
        post_comment_context_form_item: Tuple[str, BaseForm],
        CommentModel: Type[Model],
        CommentModelAdapter: CommentModelAdapterT,
        profile_content_tester: ProfilePostContentTester
):
    post_with_published_location.author = another_user
    post_with_published_location.save()
    _, ctx_form = post_comment_context_form_item
    a_post_get_response = get_a_post_get_response_safely(
        user_client, post_with_published_location.id
    )

    # create comments
    creation_tester = CreateCommentFormTester(
        a_post_get_response,
        CommentModel,
        user_client,
        another_user_client,
        unlogged_client,
        item_adapter=None,
        ModelAdapter=CommentModelAdapter,
    )

    Form: Type[BaseForm] = type(ctx_form)
    forms_to_create = create_comment_creation_forms(
        creation_tester, Form, CommentModel, CommentModelAdapter)

    response_on_created, created_items = creation_tester.test_create_several(
        forms_to_create[1:], qs=CommentModel.objects.all()
    )
    content = response_on_created.content.decode(encoding="utf8")
    creation_tester.test_creation_response(content, created_items)

    comment_count_repr = f"({len(created_items)})"

    index_content = user_client.get("/").content.decode("utf-8")
    if comment_count_repr not in index_content:
        raise AssertionError(
            "Убедитесь, что на главной странице под постами отображается"
            " количество комментариев. Число комментариев должно быть указано"
            " в круглых скобках."
        )

    # check comment count on profile page
    comment_adapter = CommentModelAdapter(created_items[0])
    comment_post_adapter = PostModelAdapter(comment_adapter.post)
    author_profile_url = f'/profile/{comment_post_adapter.author.username}/'
    profile_content = (
        profile_content_tester.user_client_testget(
            url=author_profile_url).content.decode("utf-8"))
    if comment_count_repr not in profile_content:
        raise AssertionError(
            "Убедитесь, что на странице пользователя под постами отображается"
            " количество комментариев. Число комментариев должно быть указано"
            " в круглых скобках."
        )

    created_item_adapters = [CommentModelAdapter(i) for i in created_items]

    # edit comments
    post_url = f"/posts/{post_with_published_location.id}/"
    edit_url, del_url = find_edit_and_delete_urls(
        created_item_adapters,
        response_on_created,
        urls_start_with=KeyVal(
            key=post_url.replace(
                f"/{post_with_published_location.id}/", "/<post_id>/"
            ),
            val=post_url,
        ),
        user_client=user_client,
    )

    item_to_edit = created_items[0]
    item_to_edit_adapter = CommentModelAdapter(item_to_edit)
    old_prop_value = item_to_edit_adapter.displayed_field_name_or_value
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value: (
            f"{old_prop_value} edited"
        )
    }
    delete_url_addr = del_url.key

    _test_edit(
        edit_url,
        CommentModelAdapter,
        item_to_edit,
        EditFormTester=EditCommentFormTester,
        user_client=user_client,
        another_user_client=another_user_client,
        unlogged_client=unlogged_client,
        **update_props,
    )

    item_to_delete_adapter = item_to_edit_adapter
    DeleteCommentTester(
        item_to_delete_adapter.item_cls,
        user_client,
        another_user_client,
        unlogged_client,
        item_adapter=item_to_delete_adapter,
    ).test_delete_item(
        qs=item_to_delete_adapter.item_cls.objects.all(),
        delete_url_addr=delete_url_addr,
    )

    status_404_on_edit_deleted_comment_err_msg = (
        "Убедитесь, что при обращении к странице редактирования"
        " несуществующего комментария возвращается статус 404."
    )
    try:
        response = user_client.get(edit_url[0])
    except CommentModel.DoesNotExist:
        raise AssertionError(
            status_404_on_edit_deleted_comment_err_msg
        )
    assert response.status_code == HTTPStatus.NOT_FOUND, (
        status_404_on_edit_deleted_comment_err_msg)

    def _test_delete_unexisting_comment(err_msg):
        try:
            response = user_client.get(delete_url_addr)
        except CommentModel.DoesNotExist:
            raise AssertionError(
                err_msg
            )
        assert response.status_code == HTTPStatus.NOT_FOUND, err_msg

    _test_delete_unexisting_comment(
        "Убедитесь, что при обращении к странице удаления несуществующего"
        " комментария возвращается статус 404."
    )

    item_to_edit_adapter.post.delete()
    item_to_edit_adapter.post.save()

    _test_delete_unexisting_comment(
        "Убедитесь, что при обращении к странице удаления комментария "
        "несуществующего поста возвращается статус 404."
    )


@pytest.mark.django_db(transaction=True)
def test_404_on_comment_deleted_post(
        user_client: django.test.Client,
        another_user_client: django.test.Client,
        unlogged_client: django.test.Client,
        post_with_published_location: Any,
        another_user: Model,
        post_comment_context_form_item: Tuple[str, BaseForm],
        CommentModel: Type[Model],
        CommentModelAdapter: CommentModelAdapterT,
):
    post_with_published_location.author = another_user
    post_with_published_location.save()
    _, ctx_form = post_comment_context_form_item
    a_post_get_response = get_a_post_get_response_safely(
        user_client, post_with_published_location.id
    )
    creation_tester = CreateCommentFormTester(
        a_post_get_response,
        CommentModel,
        user_client,
        another_user_client,
        unlogged_client,
        item_adapter=None,
        ModelAdapter=CommentModelAdapter,
    )

    Form: Type[BaseForm] = type(ctx_form)
    form_to_create = create_comment_creation_forms(
        creation_tester, Form, CommentModel, CommentModelAdapter,
        return_single_form=True
    )

    post_with_published_location.delete()
    post_with_published_location.save()
    creation_tester.test_create_item(
        form=form_to_create,
        qs=CommentModel.objects.all(),
        submitter=AuthorisedSubmitTester(
            creation_tester,
            test_response_cbk=(
                AuthorisedSubmitTester.get_test_response_404_cbk(
                    err_msg=(
                        "Убедитесь, что при попытке создания комментария "
                        "к несуществующему посту возвращается статус 404."
                    )
                )
            ),
        ),
        assert_created=False,
    )
