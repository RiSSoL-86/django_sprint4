from typing import Tuple, Union

import bs4
from django.db.models import QuerySet, Model
from django.forms import BaseForm
from django.http import HttpResponse

from conftest import TitledUrlRepr, UrlRepr
from fixtures.types import ModelAdapterT
from form.base_form_tester import (
    FormTagMissingException,
    FormMethodException,
    TextareaMismatchException,
    TextareaTagMissingException,
)
from form.base_form_tester import (
    SubmitTester,
    FormValidationException,
    UnauthorizedEditException,
    UnauthenticatedEditException,
    AuthenticatedEditException,
    DatabaseCreationException,
    ItemCreatedException,
)
from form.base_form_tester import (
    UnauthorizedSubmitTester,
    AnonymousSubmitTester,
)
from form.post.form_tester import PostFormTester


class EditPostFormTester(PostFormTester):
    def __init__(
        self,
        response: HttpResponse,
        *args,
        ModelAdapter: ModelAdapterT,
        **kwargs,
    ):
        try:
            super().__init__(
                response, *args, ModelAdapter=ModelAdapter, **kwargs
            )
        except FormTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что на страницу редактирования поста передаётся"
                " форма."
            ) from e

    @property
    def unauthorized_edit_redirect_cbk(self):
        redirect_to_page: TitledUrlRepr = (
            UrlRepr(r"/posts/\d+/$", "/posts/<int:post_id>/"),
            "страницу публикации",
        )
        return UnauthorizedSubmitTester.get_test_response_redirect_cbk(
            tester=self, redirect_to_page=redirect_to_page
        )

    @property
    def anonymous_edit_redirect_cbk(self):
        return AnonymousSubmitTester.get_test_response_redirect_cbk(
            tester=self, redirect_to_page="страницу аутентификации"
        )

    @property
    def textarea_tag(self) -> bs4.Tag:
        try:
            return super().textarea_tag
        except TextareaTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что в форме редактирования поста есть элемент"
                " `textarea`."
            ) from e

    def _validate(self):
        try:
            super()._validate()
        except FormTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что на страницу редактирования поста передаётся"
                " форма."
            ) from e
        except FormMethodException as e:
            raise AssertionError(
                "Убедитесь, что форма для редактирования поста отправляется"
                " методом `POST`."
            ) from e
        except TextareaMismatchException as e:
            raise AssertionError(
                "Убедитесь, что в форме редактирования поста основной текст"
                " передаётся в поле типа `textarea`."
            ) from e

    def try_create_item(
        self,
        form: BaseForm,
        qs: QuerySet,
        submitter: SubmitTester,
        assert_created: bool = True,
    ) -> Tuple[HttpResponse, Model]:
        try:
            return super().try_create_item(form, qs, submitter, assert_created)
        except FormValidationException as e:
            raise AssertionError(
                "При редактировании поста возникает ошибка:\n"
                f"{type(e).__name__}: {e}"
            ) from e

    def test_unlogged_cannot_create(
        self, form: BaseForm, qs: QuerySet
    ) -> None:
        try:
            super().test_unlogged_cannot_create(form, qs)
        except ItemCreatedException as e:
            raise AssertionError(
                "Проверьте, что если неаутентифицированный пользователь"
                " отправит форму редактирования поста - объект поста в базе"
                " данных не будет создан или изменён."
            ) from e

    def test_edit_item(
        self, updated_form: BaseForm, qs: QuerySet, item_adapter: ModelAdapterT
    ) -> HttpResponse:
        try:
            return super().test_edit_item(updated_form, qs, item_adapter)
        except UnauthorizedEditException:
            raise AssertionError(
                "Убедитесь, что пользователь не может редактировать чужие"
                " посты."
            )
        except UnauthenticatedEditException:
            raise AssertionError(
                "Убедитесь, что неаутентифицированный пользователь не может"
                " редактировать посты."
            )
        except AuthenticatedEditException:
            raise AssertionError(
                "Убедитесь, что пользователь может редактировать свои посты."
            )
        except DatabaseCreationException:
            raise AssertionError(
                "Убедитесь, что при редактировании поста в базе данных не"
                " создаётся новый объект поста."
            )

    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ) -> str:
        redirect_to_page_repr = self.get_redirect_to_page_repr(
            redirect_to_page
        )
        return (
            "Убедитесь, что при отправке формы редактирования поста"
            f" {by_user} он перенаправляется на {redirect_to_page_repr}."
        )

    def status_error_message(self, by_user: str) -> str:
        return (
            "Убедитесь, что при отправке формы редактирования поста"
            f" {by_user} не возникает ошибок."
        )

    @property
    def author_assignment_error_message(self) -> str:
        return (
            "Убедитесь, что в форму редактирования поста в поле «автор»"
            " передаётся аутентифицированный пользователь."
        )

    @property
    def display_text_error_message(self) -> str:
        return (
            "Убедитесь, что после редактирования поста новый текст"
            " отображается на странице поста."
        )

    def validation_error_message(self, student_form_fields_str: str) -> str:
        return (
            "Убедитесь, что для валидации формы редактирования поста"
            f" достаточно заполнить следующие поля: {student_form_fields_str}."
        )

    @property
    def item_not_created_assertion_msg(self):
        return (
            "Убедитесь, что при отправке формы редактирования публикации"
            " авторизованным пользователем  в базе данных не создаётся новый"
            " объект поста."
        )

    @property
    def wrong_author_assertion_msg(self):
        return (
            "Убедитесь, что при редактировании поста в форму в поле «автор»"
            " передаётся аутентифицированный пользователь."
        )

    def creation_assertion_msg(self, prop):
        return (
            "Убедитесь, что после отправки формы редактирования поста"
            " правильно работает переадресация. Проверьте, что значение поля"
            f" `{prop}` отображается на странице поста."
        )
