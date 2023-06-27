from conftest import TitledUrlRepr, UrlRepr
from form.base_form_tester import (
    UnauthorizedSubmitTester, AnonymousSubmitTester)
from form.post.form_tester import PostFormTester


class EditPostFormTester(PostFormTester):

    @property
    def of_which_action(self):
        return 'редактирования'

    @property
    def unauthorized_edit_redirect_cbk(self):
        redirect_to_page: TitledUrlRepr = (
            UrlRepr(r'/posts/\d+/$', '/posts/<int:post_id>/'),
            'страницу публикации')
        return UnauthorizedSubmitTester.get_test_response_redirect_cbk(
            tester=self,
            redirect_to_page=redirect_to_page
        )

    @property
    def anonymous_edit_redirect_cbk(self):
        return AnonymousSubmitTester.get_test_response_redirect_cbk(
            tester=self,
            redirect_to_page='страницу аутентификации')
