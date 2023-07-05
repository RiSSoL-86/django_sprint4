from abc import abstractmethod
from typing import Set, Tuple, Optional, Union

from django.db.models import QuerySet, Model
from django.http import HttpResponse

from conftest import TitledUrlRepr
from form.base_form_tester import (
    UnauthorizedSubmitTester,
    AnonymousSubmitTester,
    AuthorisedSubmitTester,
    SubmitTester,
)
from form.base_tester import BaseTester


class DeleteTester(BaseTester):
    @property
    @abstractmethod
    def unauthenticated_user_error(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def anonymous_user_error(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def successful_delete_error(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def only_one_delete_error(self):
        raise NotImplementedError

    @abstractmethod
    def status_error_message(self, by_user: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ):
        raise NotImplementedError

    def get_redirect_to_page_repr(self, redirect_to_page):
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

    def test_delete_item(
        self, qs: QuerySet, delete_url_addr: str
    ) -> HttpResponse:
        instances_before: Set[Model] = set(qs.all())

        can_delete, response = self.user_can_delete(
            UnauthorizedSubmitTester(tester=self, test_response_cbk=None),
            delete_url_addr,
            self._item_adapter,
            qs=qs,
        )
        assert not can_delete, self.unauthenticated_user_error

        can_delete, response = self.user_can_delete(
            AnonymousSubmitTester(tester=self, test_response_cbk=None),
            delete_url_addr,
            self._item_adapter,
            qs=qs,
        )
        assert not can_delete, self.anonymous_user_error

        can_delete, response = self.user_can_delete(
            AuthorisedSubmitTester(
                tester=self,
                test_response_cbk=(
                    AuthorisedSubmitTester.get_test_response_ok_cbk(
                        tester=self
                    )
                ),
            ),
            delete_url_addr,
            self._item_adapter,
            qs=qs,
        )
        assert can_delete, self.successful_delete_error

        instances_after: Set[Model] = set(qs.all())

        deleted_instances_n = instances_before - instances_after
        assert len(deleted_instances_n) == 1, self.only_one_delete_error

        return response

    def user_can_delete(
        self,
        submitter: SubmitTester,
        delete_url,
        item_to_delete_adapter,
        qs: QuerySet,
    ) -> Tuple[Optional[bool], Optional[HttpResponse]]:
        response = submitter.test_submit(url=delete_url, data={})
        deleted = qs.filter(id=item_to_delete_adapter.id).first() is None
        return deleted, response
