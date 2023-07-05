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
    UnauthorizedEditException,
    UnauthenticatedEditException,
    AuthenticatedEditException,
    DatabaseCreationException,
    ItemCreatedException,
)


class EditUserFormTester(BaseFormTester):
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
                "Убедитесь, что на страницу редактирования профиля"
                " пользователя передаётся форма."
            ) from e

    @property
    def has_textarea(self):
        return False

    @property
    def textarea_tag(self) -> bs4.Tag:
        raise NotImplementedError(
            "This tag is not applicable on user profile page."
        )

    def _validate(self):
        try:
            super()._validate()
        except FormTagMissingException as e:
            raise AssertionError(
                "Убедитесь, что на страницу редактирования профиля"
                " пользователя передаётся форма."
            ) from e
        except FormMethodException as e:
            raise AssertionError(
                "Убедитесь, что форма редактирования профиля пользователя"
                " отправляется методом `POST`."
            ) from e
        except TextareaMismatchException:
            pass

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
                "При редактировании профиля пользователя возникает ошибка:\n"
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
                " отправит форму редактирования профиля - объект пользователя"
                " в базе данных не будет создан или изменён."
            ) from e

    def test_edit_item(
        self, updated_form: BaseForm, qs: QuerySet, item_adapter: ModelAdapterT
    ) -> HttpResponse:
        try:
            return super().test_edit_item(updated_form, qs, item_adapter)
        except UnauthorizedEditException:
            raise AssertionError(
                "Убедитесь, что пользователь не может редактировать чужой"
                " профиль пользователя."
            )
        except UnauthenticatedEditException:
            raise AssertionError(
                "Убедитесь, что неаутентифицированный пользователь не может"
                " редактировать профиль пользователя."
            )
        except AuthenticatedEditException:
            raise AssertionError(
                "Убедитесь, что пользователь может редактировать свой"
                " профиль."
            )
        except DatabaseCreationException:
            raise AssertionError(
                "Убедитесь, что при редактировании профиля пользователя в"
                " базе данных не создаётся новый объект профиля пользователя."
            )

    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ) -> str:
        redirect_to_page_repr = self.get_redirect_to_page_repr(
            redirect_to_page
        )
        return (
            "Убедитесь, что после отправки формы редактирования профиля"
            f" пользователя {by_user} он перенаправляется на"
            f" {redirect_to_page_repr}."
        )

    def status_error_message(self, by_user: str) -> str:
        return (
            "Убедитесь, что при отправке формы редактирования профиля"
            f" пользователя {by_user} не возникает ошибок."
        )

    @property
    def author_assignment_error_message(self) -> str:
        return (
            "Убедитесь, что в форму редактирования профиля пользователя в поле"
            " «автор» передаётся аутентифицированный пользователь."
        )

    @property
    def display_text_error_message(self) -> str:
        return (
            "Убедитесь, что после редактировании профиля пользователя новый"
            " текст отображается на странице профиля."
        )

    def validation_error_message(self, student_form_fields_str: str) -> str:
        return (
            "Убедитесь, что для валидации формы редактирования профиля"
            " пользователя достаточно заполнить следующие поля:"
            f" {student_form_fields_str}."
        )

    @property
    def item_not_created_assertion_msg(self):
        return (
            "Убедитесь, что при отправке формы редактирования профиля"
            " пользователя авторизованным пользователем в базе данных не"
            " создаётся новый профиль пользователя."
        )

    @property
    def wrong_author_assertion_msg(self):
        raise NotImplementedError(
            "User profiles are not supposed to be created from code."
        )

    def creation_assertion_msg(self, prop):
        return (
            "Убедитесь, что после отправки формы редактировании профиля"
            " пользователя правильно работает  переадресация. Проверьте, что"
            f" значение поля `{prop}` отображается на странице профиля."
        )
