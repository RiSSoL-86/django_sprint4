from typing import Tuple, Union

import bs4
from django.db.models import QuerySet, Model
from django.forms import BaseForm
from django.http import HttpResponse

from conftest import TitledUrlRepr
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
    BaseFormTester,
    ItemCreatedException,
)


class CreateCommentFormTester(BaseFormTester):
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
                "Убедитесь, что для аутентифицированного пользователя на"
                " страницу поста передаётся форма для создания комментария."
            ) from e

    @property
    def has_textarea(self):
        return True

    @property
    def textarea_tag(self) -> bs4.Tag:
        try:
            return super().textarea_tag
        except TextareaTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что в форме для создания комментария есть поле"
                " типа `textarea` для ввода текста."
            ) from e

    def _validate(self):
        try:
            super()._validate()
        except FormTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что для аутентифицированного пользователя на"
                " страницу поста передаётся форма для создания комментария."
            ) from e
        except FormMethodException as e:
            raise AssertionError(
                "Убедитесь, что форма для создания комментария отправляется"
                " методом `POST`."
            ) from e
        except TextareaMismatchException as e:
            raise AssertionError(
                "Убедитесь, что в форме создания комментария текст"
                " комментария передаётся через поле типа `textarea`."
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
                "При создании комментария возникает ошибка:\n"
                f"{type(e).__name__}: {e}"
            ) from e

    def test_unlogged_cannot_create(
        self, form: BaseForm, qs: QuerySet
    ) -> None:
        try:
            super().test_unlogged_cannot_create(form, qs)
        except ItemCreatedException as e:
            raise AssertionError(
                "Убедитесь, что при отправке комментария"
                " неаутентифицированным пользователем в базе данных не"
                " создаётся объект комментария."
            ) from e

    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ) -> str:
        redirect_to_page_repr = self.get_redirect_to_page_repr(
            redirect_to_page
        )
        return (
            "Убедитесь, что при отправке формы создания комментария"
            f" {by_user} он перенаправляется на {redirect_to_page_repr}."
        )

    def status_error_message(self, by_user: str) -> str:
        return (
            "Убедитесь, что при отправке формы для создания комментария"
            f" {by_user} не возникает ошибок."
        )

    @property
    def author_assignment_error_message(self) -> str:
        return (
            "Убедитесь, что при создании комментария в форму в поле «автор»"
            " передаётся аутентифицированный пользователь."
        )

    @property
    def display_text_error_message(self) -> str:
        return (
            "Убедитесь, что после создании комментария его текст отображается"
            " на странице поста в списке комментариев."
        )

    def validation_error_message(self, student_form_fields_str: str) -> str:
        return (
            "Убедитесь, что для валидации формы создания комментария"
            f" достаточно заполнить следующие поля: {student_form_fields_str}."
        )

    @property
    def item_not_created_assertion_msg(self):
        return (
            "Убедитесь, что при отправке формы создания комментария"
            " авторизованным пользователем в базе данных создаётся один и"
            " только один объект комментария."
        )

    @property
    def wrong_author_assertion_msg(self):
        return (
            "Убедитесь, что при создании комментария в форму в поле «автор»"
            " передаётся аутентифицированный пользователь."
        )

    def creation_assertion_msg(self, prop):
        return (
            "Убедитесь, что при создании комментария правильно настроена"
            f" переадресация, и значение поля `{prop}` отображается на"
            " странице поста, к которому относится комментарий."
        )
