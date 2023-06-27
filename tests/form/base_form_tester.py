from __future__ import annotations

import re
from abc import abstractmethod, ABC
from functools import partial
from http import HTTPStatus
from typing import (
    Set, Tuple, Type, Sequence, Callable, Optional, Dict, Iterable, Any, List,
    Union)

import bs4
import django.test
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model, QuerySet
from django.forms import BaseForm
from django.http import HttpResponse

from conftest import (
    ItemCreatedException, ItemNotCreatedException, restore_cleaned_data,
    TitledUrlRepr)
from fixtures.types import ModelAdapterT
from form.base_tester import BaseTester


class FormValidationException(Exception):
    ...


class BaseFormTester(BaseTester):

    def __init__(self, response: HttpResponse,
                 *args, ModelAdapter: ModelAdapterT, **kwargs):
        super().__init__(*args, **kwargs)

        soup = bs4.BeautifulSoup(response.content, features='html.parser')

        form_tag = soup.find('form')
        assert form_tag, (
            f'Убедитесь, что передаёте {self.to_which_page} {self.which_form}.'
        )

        self._form_tag = form_tag
        self._action = self._form_tag.get('action', '') or (
            response.request['PATH_INFO']
        )
        self._ModelAdapter = ModelAdapter

        self._validate()

    @property
    @abstractmethod
    def has_textarea(self):
        ...

    @property
    def what_form(self):
        return f'форма для {self.of_which_action} {self.of_which_obj}'

    @property
    def which_form(self):
        return f'форму для {self.of_which_action} {self.of_which_obj}'

    @property
    def in_which_form(self):
        return f'в форме для {self.of_which_action} {self.of_which_obj}'

    @property
    def of_which_form(self):
        return f'формы для {self.of_which_action} {self.of_which_obj}'

    @property
    def unauthorized_edit_redirect_cbk(self):
        return None

    @property
    def anonymous_edit_redirect_cbk(self):
        return None

    def redirect_error_message(self, by_user: str,
                               redirect_to_page: Union[TitledUrlRepr, str]):
        if isinstance(redirect_to_page, str):
            redirect_to_page_repr = redirect_to_page
        elif isinstance(redirect_to_page, tuple):  # expected TitledUrlRepr
            (
                redirect_pattern, redirect_repr
            ), redirect_title = redirect_to_page
            redirect_to_page_repr = f'{redirect_title} ({redirect_repr})'
        else:
            raise AssertionError(
                f'Unexpected value type `{type(redirect_to_page)}` '
                f'for `redirect_to_page`')
        return (
            f'Убедитесь, что при отправке {self.of_which_form} '
            f'{self.on_which_page} {by_user} '
            f'он перенаправляется на {redirect_to_page_repr}.'
        )

    def status_error_message(self, by_user: str):
        return (
            f'Убедитесь, что при отправке {self.of_which_form} '
            f'{by_user} {self.of_which_obj} не возникает ошибок.')

    @property
    def textarea_tag(self) -> bs4.Tag:
        textarea = self._form_tag.find('textarea')
        assert textarea, (
            'Убедитесь, что создан элемент формы `textarea` '
            f'для введения текста {self.of_which_obj} '
            f'{self.in_which_form} {self.on_which_page}.'
        )
        return textarea

    def _validate(self):
        assert self._form_tag, (
            f'Убедитесь, что передаёте {self.to_which_page} {self.which_form}.'
        )
        assert self._form_tag.get('method', 'get').upper() == 'POST', (
            f'Убедитесь, что {self.what_form} {self.on_which_page} '
            'отправляется методом `POST`.'
        )
        if self.has_textarea and self._item_adapter:
            assert self.textarea_tag.text.strip(
            ) == self._item_adapter.text.strip(), (
                f'Убедитесь, что текст {self.of_which_obj} привязан к полю '
                f'типа `textarea` {self.in_which_form} {self.on_which_page}.'
            )

    def try_create_item(
            self, form: BaseForm, qs: QuerySet,
            submitter: SubmitTester,
            assert_created: bool = True
    ) -> Tuple[HttpResponse, Model]:

        if not form.is_valid():
            raise FormValidationException(form.errors)
        elif form.errors:
            raise FormValidationException(form.errors)

        items_before = set(qs.all())

        restored_data = restore_cleaned_data(form.cleaned_data)
        try:
            response = submitter.test_submit(
                url=self._action, data=restored_data)
        except Exception as e:
            raise AssertionError(
                f'При создании {self.of_which_obj} {self.on_which_page} '
                f'возникает ошибка:\n'
                f'{type(e).__name__}: {e}'
            )

        items_after: Set[Model] = set(qs.all())
        created_items = items_after - items_before
        n_created = len(created_items)
        created = next(iter(created_items)) if created_items else None

        if assert_created:
            if not n_created:
                raise ItemNotCreatedException
        elif n_created:
            raise ItemCreatedException(n_created)

        return response, created

    @staticmethod
    def init_create_item_form(
            Form: Type[BaseForm], **form_data
    ) -> BaseForm:
        return Form(data=form_data)

    def init_create_item_forms(
            self, Form: Type[BaseForm], Model: Type[Model],
            ModelAdapter: ModelAdapterT,
            forms_unadapted_data: Iterable[Dict[str, Any]]
    ) -> List[BaseForm]:
        creation_forms = []

        model_adapter = ModelAdapter(Model)
        for unadapted_form_data in forms_unadapted_data:
            adapted_form_data = {}
            for k, v in unadapted_form_data.items():
                adapted_form_data[getattr(model_adapter, k).field.name] = v
            creation_forms.append(
                self.init_create_item_form(
                    Form, **adapted_form_data)
            )

        return creation_forms

    def test_unlogged_cannot_create(self, form: BaseForm,
                                    qs: QuerySet) -> None:
        try:
            self.test_create_item(
                form, qs,
                AnonymousSubmitTester(
                    self,
                    test_response_cbk=None),
                assert_created=False)

        except ItemCreatedException:
            raise AssertionError(
                f'Убедитесь, что {self.on_which_page} '
                f'отправка {self.of_which_form} '
                f'неаутентифицированным пользователем '
                f'не создаёт объект {self.of_which_obj} в базе данных.'
            )
        pass

    def test_create_item(
            self, form: BaseForm, qs: QuerySet,
            submitter: SubmitTester,
            assert_created: bool = True
    ) -> Tuple[HttpResponse, Model]:

        try:
            response, created = self.try_create_item(
                form, qs, submitter, assert_created)
        except FormValidationException:
            student_form_fields = [
                self._ModelAdapter(form.Meta.model).get_student_field_name(k)
                for k in form.data.keys()]
            student_form_fields_str = ', '.join(student_form_fields)
            raise AssertionError(
                f'Убедитесь, что для валидации {self.of_which_form} '
                f'достаточно заполнения следующих полей: '
                f'{student_form_fields_str}.'
            )
        if assert_created:
            assert self._ModelAdapter(
                created).author == response.wsgi_request.user, (
                f'Убедитесь, что при создании {self.of_which_obj} '
                f'{self.on_which_page} в поле автора {self.of_which_obj} '
                'присваивается аутентифицированный пользователь.'
            )
            content = response.content.decode(encoding='utf8')
            if self._ModelAdapter(created).text in content:
                if not assert_created:
                    raise AssertionError(
                        f'Убедитесь, что при создании {self.of_which_obj} '
                        f'{self.on_which_page} текст {self.of_which_obj} '
                        'отображается на странице ответа.'
                    )

        return response, created

    def test_create_several(
            self, forms: Iterable[BaseForm], qs: QuerySet
    ) -> Tuple[HttpResponse, List[Model]]:

        created_items = []
        for form in forms:
            try:
                response, created = self.test_create_item(
                    form, qs,
                    AuthorisedSubmitTester(
                        self,
                        test_response_cbk=(
                            AuthorisedSubmitTester.get_test_response_ok_cbk(
                                tester=self
                            ))),
                    assert_created=True)
            except ItemNotCreatedException:
                raise AssertionError(
                    'Убедитесь, что при отправке '
                    f'авторизованным пользователем {self.of_which_form} '
                    f'{self.on_which_page}'
                    f'в базе данных создаётся {self.one_and_only_one} '
                    f'{self.which_obj}.')

            created_items.append(created)
            assert self._ModelAdapter(
                created).author == response.wsgi_request.user, (
                f'Убедитесь, что при создании {self.of_which_obj} '
                f'{self.on_which_page} в поле автора {self.of_which_obj} '
                'присваивается аутентифицированный пользователь.'
            )

        # noinspection PyUnboundLocalVariable
        return response, created_items

    @staticmethod
    def init_create_form_from_item(
            item: Model,
            Form: Type[BaseForm],
            ModelAdapter: ModelAdapterT,
            file_data: Optional[Dict[str, SimpleUploadedFile]],
            **update_form_data
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

    def test_creation_response(
            self, content: str, created_items: Iterable[Model]):
        for item in created_items:
            item_adapter = self._ModelAdapter(item)
            prop = item_adapter.item_cls_adapter.displayed_field_name_or_value
            if not self._ModelAdapter(item).text in content:
                raise AssertionError(
                    f'Убедитесь, что при создании {self.of_which_obj} '
                    f'{self.on_which_page} правильно настроена '
                    f'переадресация, и значение поля '
                    f'`{item_adapter.get_student_field_name(prop)}` '
                    'отображается на странице ответа.'
                )

    def test_edit_item(
            self, updated_form: BaseForm, qs: QuerySet,
            item_adapter: ModelAdapterT
    ) -> HttpResponse:

        instances_before: Set[Model] = set(qs.all())

        can_edit, _ = self.user_can_edit(
            self.another_user_client,
            submitter=UnauthorizedSubmitTester(
                tester=self,
                test_response_cbk=self.unauthorized_edit_redirect_cbk),
            item_adapter=item_adapter, updated_form=updated_form)
        assert can_edit is not True, (
            f'Убедитесь, что редактирование {self.of_which_obj} недоступно '
            'неавторизованному пользователю.')

        can_edit, _ = self.user_can_edit(
            self.unlogged_client,
            submitter=AnonymousSubmitTester(
                tester=self,
                test_response_cbk=self.anonymous_edit_redirect_cbk),
            item_adapter=item_adapter, updated_form=updated_form)
        assert can_edit is not True, (
            f'Убедитесь, что редактирование {self.of_which_obj} недоступно '
            'неаутентифицированному пользователю.')

        can_edit, response = self.user_can_edit(
            self.user_client,
            submitter=AuthorisedSubmitTester(
                tester=self,
                test_response_cbk=(
                    AuthorisedSubmitTester.get_test_response_ok_cbk(
                        tester=self
                    ))),
            item_adapter=item_adapter, updated_form=updated_form)
        assert can_edit, (
            f'Убедитесь, что авторизованному пользователю доступно '
            f'редактирование {self.of_which_obj} и вносимые им '
            f'изменения сохраняются.')

        instances_after: Set[Model] = set(qs.all())

        created_instances_n = instances_after - instances_before
        assert len(created_instances_n) == 0, (
            f'Убедитесь, что при отправке {self.of_which_form} '
            f'{self.on_which_page} в базе данных не создаётся '
            f'{self.which_obj}.')

        return response

    def user_can_edit(
            self, client, submitter: SubmitTester, item_adapter, updated_form
    ) -> Tuple[Optional[bool], Optional[HttpResponse]]:
        if not client:
            return None, None
        disp_old_value = item_adapter.displayed_field_name_or_value
        response = submitter.test_submit(
            url=self._action, data=updated_form.data)
        item_adapter.refresh_from_db()
        disp_new_value = item_adapter.displayed_field_name_or_value
        return disp_new_value != disp_old_value, response


class SubmitTester(ABC):
    __slots__ = [
        'expected_codes', 'client', '_test_response_cbk', '_tester']

    def __init__(
            self, tester: BaseTester,
            test_response_cbk: Optional[Callable[[HttpResponse], None]]
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
                response.status_code in assert_status_not_in):
            raise AssertionError(err_msg)
        if assert_redirect is not None and assert_redirect:
            assert hasattr(response, 'redirect_chain') and getattr(
                response, 'redirect_chain'), err_msg
            if isinstance(assert_redirect, tuple):  # expected TitledUrlRepr
                (redirect_pattern,
                 redirect_repr), redirect_title = assert_redirect
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
            by_user: Optional[str] = None
    ):
        by_user = by_user or 'пользователь'
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.OK,),
            assert_redirect=redirect_to_page,
            err_msg=tester.redirect_error_message(by_user, redirect_to_page))

    @staticmethod
    def get_test_response_ok_cbk(
            tester: BaseTester,
            by_user: Optional[str] = None
    ):
        by_user = by_user or 'авторизованным пользователем'
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.OK,),
            err_msg=tester.status_error_message(by_user))

    @staticmethod
    def get_test_response_404_cbk(
            tester: BaseTester,
            by_user: Optional[str] = None
    ):
        by_user = by_user or 'авторизованным пользователем'
        return partial(
            SubmitTester.test_response_cbk,
            assert_status_in=(HTTPStatus.NOT_FOUND,),
            err_msg=(
                f'Убедитесь, что если {tester.which_obj} не существует, то '
                f'при отправке запроса {by_user} {tester.to_which_page} '
                f'возникает ошибка 404.'
            ))


class AuthorisedSubmitTester(SubmitTester):

    def __init__(
            self,
            tester: BaseTester,
            test_response_cbk: Optional[Callable[[HttpResponse], None]]
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.user_client

    @staticmethod
    def get_test_response_redirect_cbk(
            tester: BaseTester,
            by_user: Optional[str] = None,
            redirect_to_page: Optional[str] = None
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or 'авторизованным пользователем',
            redirect_to_page=redirect_to_page)

    @staticmethod
    def get_test_response_ok_cbk(
            tester: BaseTester,
            by_user: Optional[str] = None
    ):
        return SubmitTester.get_test_response_ok_cbk(
            tester=tester,
            by_user=by_user or 'авторизованным пользователем')

    @staticmethod
    def get_test_response_404_cbk(
            tester: BaseTester,
            by_user: Optional[str] = None
    ):
        return SubmitTester.get_test_response_404_cbk(
            tester=tester,
            by_user=by_user or 'авторизованным пользователем')


class UnauthorizedSubmitTester(SubmitTester):

    def __init__(
            self, tester: BaseTester,
            test_response_cbk: Optional[Callable[[HttpResponse], None]]
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.another_user_client

    @staticmethod
    def get_test_response_redirect_cbk(
            tester: BaseTester,
            redirect_to_page: Union[TitledUrlRepr, str],
            by_user: Optional[str] = None
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or 'неавторизованным пользователем',
            redirect_to_page=redirect_to_page)


class AnonymousSubmitTester(SubmitTester):

    def __init__(
            self, tester: BaseTester,
            test_response_cbk: Optional[Callable[[HttpResponse], None]]
    ):
        super().__init__(tester, test_response_cbk=test_response_cbk)
        self.client = tester.unlogged_client

    @staticmethod
    def get_test_response_redirect_cbk(
            tester: BaseTester,
            redirect_to_page: Optional[str] = None,
            by_user: Optional[str] = None
    ):
        return SubmitTester.get_test_response_redirect_cbk(
            tester=tester,
            by_user=by_user or 'неаутентифицированным пользователем',
            redirect_to_page=redirect_to_page or 'страницу аутентификации')
