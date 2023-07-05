from typing import Union

from conftest import TitledUrlRepr
from form.delete_tester import DeleteTester


class DeleteCommentTester(DeleteTester):
    @property
    def unauthenticated_user_error(self):
        return (
            "Убедитесь, что комментарий может быть удалён только автором и"
            " администратором, но не другими аутентифицированными"
            " пользователями."
        )

    @property
    def anonymous_user_error(self):
        return (
            "Убедитесь, что комментарий может быть удалён только автором и"
            " администратором, но не другими аутентифицированными"
            " пользователями."
        )

    @property
    def successful_delete_error(self):
        return (
            "Убедитесь, что после отправки запроса на удаление комментария"
            " этот комментарий не отображается на странице поста, к которому"
            " он относился."
        )

    @property
    def only_one_delete_error(self):
        return (
            "Убедитесь, что при отправке запроса на удаление комментария"
            " объект комментария удаляется из базы данных."
        )

    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ):
        return (
            "Убедитесь, что при отправке запроса на удаление комментария"
            f" {by_user} он перенаправляется на страницу поста."
        )

    def status_error_message(self, by_user: str) -> str:
        return (
            "Убедитесь, что при отправке запроса на удаление комментария"
            f" {by_user} не возникает ошибок."
        )

    @property
    def nonexistent_obj_error_message(self):
        return (
            "Проверьте, что если авторизованный пользователь отправит запрос к"
            " странице удаления несуществующего комментария - возникнет ошибка"
            " 404."
        )
