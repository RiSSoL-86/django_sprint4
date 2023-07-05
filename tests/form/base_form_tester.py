from __future__ import annotations

import re
from abc import abstractmethod, ABC
from functools import partial
from http import HTTPStatus
from typing import (
    Set,
    Tuple,
    Type,
    Sequence,
    Callable,
    Optional,
    Dict,
    Iterable,
    Any,
    List,
    Union,
)

import bs4
import django.test
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model, QuerySet
from django.forms import BaseForm
from django.http import HttpResponse

from conftest import (
    ItemNotCreatedException,
    restore_cleaned_data,
    TitledUrlRepr,
)
from fixtures.types import ModelAdapterT
from form.base_tester import BaseTester


class FormValidationException(Exception):
    pass


class FormTagMissingException(FormValidationException):
    pass


class FormMethodException(FormValidationException):
    pass


class TextareaMismatchException(FormValidationException):
    pass


class FormValidationException(Exception):
    pass


class ItemCreatedException(Exception):
    pass


class UnauthorizedEditException(Exception):
    pass


class UnauthenticatedEditException(Exception):
    pass


class AuthenticatedEditException(Exception):
    pass


class DatabaseCreationException(Exception):
    pass


class TextareaTagMissingException(Exception):
    pass


class BaseFormTester(BaseTester):
    def __init__(
        self,
        response: HttpResponse,
        *args,
        ModelAdapter: ModelAdapterT,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        soup = bs4.BeautifulSoup(response.content, features="html.parser")

        form_tag = soup.find("form")
        if not form_tag:
            raise FormTagMissingException()

        self._form_tag = form_tag
        self._action = self._form_tag.get("action", "") or (
            response.request["PATH_INFO"]
        )
        self._ModelAdapter = ModelAdapter

        self._validate()

    @property
    @abstractmethod
    def has_textarea(self):
        ...

    @property
    def unauthorized_edit_redirect_cbk(self):
        return None

    @property
    def anonymous_edit_redirect_cbk(self):
        return None

    @abstractmethod
    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def author_assignment_error_message(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def display_text_error_message(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def validation_error_message(self, student_form_fields_str: str) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def item_not_created_assertion_msg(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def wrong_author_assertion_msg(self):
        raise NotImplementedError

    def get_redirect_to_page_repr(self, redirect_to_page) -> str:
        if isinstance(redirect_to_page, str):
            redirect_to_page_repr = redirect_to_page
        elif isinstance(redirect_to_page, tuple):  # expected TitledUrlRepr
            (
                redirect_pattern,
                redirect_repr,
            ), redirect_title = redirect_to_page
            redirect_to_page_repr = f"{redirect_title} ({redirect_repr})"
        else:
            raise AssertionError(
                f"Unexpected value type `{type(redirect_to_page)}` "
                "for `redirect_to_page`"
            )
        return redirect_to_page_repr

    @abstractmethod
    def status_error_message(self, by_user: str) -> str:
        raise NotImplementedError

    @property
    def textarea_tag(self) -> bs4.Tag:
        textarea = self._form_tag.find("textarea")
        if not textarea:
            raise TextareaTagMissingException()
        return textarea

    def _validate(self):
        if not self._form_tag:
            raise FormTagMissingException()

        if self._form_tag.get("method", "get").upper() != "POST":
            raise FormMethodException()

        if self.has_textarea and self._item_adapter:
            textarea = self.textarea_tag
            if textarea.text.strip() != self._item_adapter.text.strip():
                raise TextareaMismatchException()

    def try_create_item(
        self,
        form: BaseForm,
        qs: QuerySet,
        submitter: SubmitTester,
        assert_created: bool = True,
    ) -> Tuple[HttpResponse, Model]:
        if not form.is_valid():
            raise FormValidationException(form.errors)
        elif form.errors:
            raise FormValidationException(form.errors)

        items_before = set(qs.all())

        restored_data = restore_cleaned_data(form.cleaned_data)
        try:
            response = submitter.test_submit(
                url=self._action, data=restored_data
            )
        except Exception:
            raise FormValidationException()

        items_after: Set[Model] = set(qs.all())
        created_items = items_after - items_before
        n_created = len(created_items)
        created = next(iter(created_items)) if created_items else None

        if assert_created:
            if not n_created:
                raise ItemNotCreatedException()
        elif n_created:
            raise ItemCreatedException()

        return response, created

    @staticmethod
    def init_create_item_form(Form: Type[BaseForm], **form_data) -> BaseForm:
        return Form(data=form_data)

    def init_create_item_forms(
        self,
        Form: Type[BaseForm],
        Model: Type[Model],
        ModelAdapter: ModelAdapterT,
        forms_unadapted_data: Iterable[Dict[str, Any]],
    ) -> List[BaseForm]:
        creation_forms = []

        model_adapter = ModelAdapter(Model)
        for unadapted_form_data in forms_unadapted_data:
            adapted_form_data = {}
            for k, v in unadapted_form_data.items():
                adapted_form_data[getattr(model_adapter, k).field.name] = v
            creation_forms.append(
                self.init_create_item_form(Form, **adapted_form_data)
            )

        return creation_forms

    def test_unlogged_cannot_create(
        self, form: BaseForm, qs: QuerySet
    ) -> None:
        self.test_create_item(
            form,
            qs,
            AnonymousSubmitTester(self, test_response_cbk=None),
            assert_created=False,
        )

    def test_create_item(
        self,
        form: BaseForm,
        qs: QuerySet,
        submitter: SubmitTester,
        assert_created: bool = True,
    ) -> Tuple[HttpResponse, Model]:
        try:
            response, created = self.try_create_item(
                form, qs, submitter, assert_created
            )
        except FormValidationException:
            student_form_fields = [
                self._ModelAdapter(form.Meta.model).get_student_field_name(k)
                for k in form.data.keys()
            ]
            student_form_fields_str = ", ".join(student_form_fields)
            raise AssertionError(
                self.validation_error_message(student_form_fields_str)
            )
        if assert_created:
            assert (
                self._ModelAdapter(created).author
                == response.wsgi_request.user
            ), self.author_assignment_error_message
            content = response.content.decode(encoding="utf8")
            if self._ModelAdapter(created).text in content:
                if not assert_created:
                    raise AssertionError(self.display_text_error_message)

        return response, created

    def test_create_several(
        self, forms: Iterable[BaseForm], qs: QuerySet
    ) -> Tuple[HttpResponse, List[Model]]:
        created_items = []
        for form in forms:
            try:
                response, created = self.test_create_item(
                    form,
                    qs,
                    AuthorisedSubmitTester(
                        self,
                        test_response_cbk=(
                            AuthorisedSubmitTester.get_test_response_ok_cbk(
                                tester=self
                            )
                        ),
                    ),
                    assert_created=True,
                )
            except ItemNotCreatedException:
                raise AssertionError(self.item_not_created_assertion_msg)

            created_items.append(created)
            assert (
                self._ModelAdapter(created).author
                == response.wsgi_request.user
            ), self.wrong_author_assertion_msg

        # noinspection PyUnboundLocalVariable
        return response, created_items

    @staticmethod
    def init_create_form_from_item(
        item: Model,
        Form: Type[BaseForm],
        ModelAdapter: ModelAdapterT,
        file_data: Optional[Dict[str, SimpleUploadedFile]],
        **update_form_data,
    ) -> BaseForm:
        form = Form(instance=item)
        form_data = form.initial

        # update from kwargs
        model_adapter = ModelAdapter(item.__class__)
        for k, v in update_form_data.items():
            form_data.update({getattr(model_adapter, k).field.name: v})

        # replace related objects with their ids for future validation
        form_data = {
            k: v.id if isinstance(v, Model) else v
            for k, v in form_data.items()
        }

        if file_data:
            for k in file_data:
                del form_data[k]

        result = Form(data=form_data, files=file_data)
        return result

    @abstractmethod
    def creation_assertion_msg(self, prop):
        pass

    def test_creation_response(
        self, content: str, created_items: Iterable[Model]
    ):
        for item in created_items:
            item_adapter = self._ModelAdapter(item)
            prop = item_adapter.item_cls_adapter.displayed_field_name_or_value
            if not self._ModelAdapter(item).text in content:
                raise AssertionError(
                    self.creation_assertion_msg(
                        item_adapter.get_student_field_name(prop)
                    )
                )

    def test_edit_item(
        self, updated_form: BaseForm, qs: QuerySet, item_adapter: ModelAdapterT
    ) -> HttpResponse:
        instances_before: Set[Model] = set(qs.all())

        can_edit, _ = self.user_can_edit(
            self.another_user_client,
            submitter=UnauthorizedSubmitTester(
                tester=self,
                test_response_cbk=self.unauthorized_edit_redirect_cbk,
            ),
            item_adapter=item_adapter,
            updated_form=updated_form,
        )

        if can_edit:
            raise UnauthorizedEditException()

        can_edit, _ = self.user_can_edit(
            self.unlogged_client,
            submitter=AnonymousSubmitTester(
                tester=self, test_response_cbk=self.anonymous_edit_redirect_cbk
            ),
            item_adapter=item_adapter,
            updated_form=updated_form,
        )

        if can_edit:
            raise UnauthenticatedEditException()

        can_edit, response = self.user_can_edit(
            self.user_client,
            submitter=AuthorisedSubmitTester(
                tester=self,
                test_response_cbk=(
                    AuthorisedSubmitTester.get_test_response_ok_cbk(
                        tester=self
                    )
                ),
            ),
            item_adapter=item_adapter,
            updated_form=updated_form,
        )

        if not can_edit:
            raise AuthenticatedEditException()

        instances_after: Set[Model] = set(qs.all())

        created_instances_n = instances_after - instances_before

        if len(created_instances_n) != 0:
            raise DatabaseCreationException()

        return response

    def user_can_edit(
        self, client, submitter: SubmitTester, item_adapter, updated_form
    ) -> Tuple[Optional[bool], Optional[HttpResponse]]:
        if not client:
            return None, None
        disp_old_value = item_adapter.displayed_field_name_or_value
        response = submitter.test_submit(
            url=self._action, data=updated_form.data
        )
        item_adapter.refresh_from_db()
        disp_new_value = item_adapter.displayed_field_name_or_value
        return disp_new_value != disp_old_value, response


class SubmitTester(ABC):
    __slots__ = ["expected_codes", "client", "_test_response_cbk", "_tester"]

    def __init__(
        self,
        tester: BaseTester,
        test_response_cbk: Optional[Callable[[HttpResponse], None]],
    ):
        self._tester = tester
        self._test_response_cbk = test_response_cbk

    def test_submit(self, url: str, data: dict) -> HttpResponse:
        assert isinstance(self.client, django.test.Client)
        response = self.client.post(url, data=data, follow=True)
        if self._test_response_cbk:
            self._test_response_cbk(response)
        return response

    @staticmethod
    def test_response_cbk(
        response: HttpResponse,
        err_msg: str,
        assert_status_in: Sequence[int] = tuple(),
        assert_status_not_in: Sequence[int] = tuple(),
        assert_redirect: Optional[Union[TitledUrlRepr, bool]] = None,
    ):
        if assert_status_in and response.status_code not in assert_status_in:
            raise AssertionError(err_msg)
        if assert_status_not_in and (
            response.status_code in assert_status_not_in
        ):
            raise AssertionError(err_msg)
        if assert_redirect is not None and assert_redirect:
            assert hasattr(response, "redirect_chain") and getattr(
                response, "redirect_chain"
            ), err_msg
            if isinstance(assert_redirect, tuple):  # expected TitledUrlRepr
                (
                    redirect_pattern,
                    redirect_repr,
                ), redirect_title = assert_redirect
                redirect_match = False
                for redirect_url, _ in response.redirect_chain:
                    if re.match(redirect_pattern, redirect_url):
                        redirect_match = True
                        break
                assert redirect_match, err_msg

    @staticmethod
    def get_test_response_redirect_cbk(
        tester: BaseTester,
        redirect_to_page: Union[TitledUrlRepr, str],
        by_user: Optional[str] = None,
    ):
        by_user = by_user or "пользователь"
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.OK,),
            assert_redirect=redirect_to_page,
            err_msg=tester.redirect_error_message(by_user, redirect_to_page),
        )

    @staticmethod
    def get_test_response_ok_cbk(
        tester: BaseTester, by_user: Optional[str] = None
    ):
        by_user = by_user or "авторизованным пользователем"
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.OK,),
            err_msg=tester.status_error_message(by_user),
        )

    @staticmethod
    def get_test_response_404_cbk(err_msg: str):
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.NOT_FOUND,),
            err_msg=err_msg,
        )


class AuthorisedSubmitTester(SubmitTester):
    def __init__(
        self,
        tester: BaseTester,
        test_response_cbk: Optional[Callable[[HttpResponse], None]],
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.user_client

    @staticmethod
    def get_test_response_redirect_cbk(
        tester: BaseTester,
        by_user: Optional[str] = None,
        redirect_to_page: Optional[str] = None,
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or "авторизованным пользователем",
            redirect_to_page=redirect_to_page,
        )

    @staticmethod
    def get_test_response_ok_cbk(
        tester: BaseTester, by_user: Optional[str] = None
    ):
        return SubmitTester.get_test_response_ok_cbk(
            tester=tester, by_user=by_user or "авторизованным пользователем"
        )


class UnauthorizedSubmitTester(SubmitTester):
    def __init__(
        self,
        tester: BaseTester,
        test_response_cbk: Optional[Callable[[HttpResponse], None]],
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.another_user_client

    @staticmethod
    def get_test_response_redirect_cbk(
        tester: BaseTester,
        redirect_to_page: Union[TitledUrlRepr, str],
        by_user: Optional[str] = None,
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or "неавторизованным пользователем",
            redirect_to_page=redirect_to_page,
        )


class AnonymousSubmitTester(SubmitTester):
    def __init__(
        self,
        tester: BaseTester,
        test_response_cbk: Optional[Callable[[HttpResponse], None]],
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.unlogged_client

    @staticmethod
    def get_test_response_redirect_cbk(
        tester: BaseTester,
        redirect_to_page: Optional[str] = None,
        by_user: Optional[str] = None,
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or "неаутентифицированным пользователем",
            redirect_to_page=redirect_to_page or "страницу аутентификации",
        )
