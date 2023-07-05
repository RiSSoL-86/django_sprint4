from typing import Union

from conftest import TitledUrlRepr
from form.delete_tester import DeleteTester


class DeletePostTester(DeleteTester):
    @property
    def unauthenticated_user_error(self):
        return (
            "Убедитесь, что пост может быть удалён только автором и"
            " администратором, но не другими аутентифицированными"
            " пользователями."
        )

    @property
    def anonymous_user_error(self):
        return (
            "Убедитесь, что пост не может быть удалён неаутентифицированным"
            " пользователем."
        )

    @property
    def successful_delete_error(self):
        return (
            "Убедитесь, что после отправки запроса на удаление поста этот пост"
            " не отображается в списке постов."
        )

    @property
    def only_one_delete_error(self):
        return (
            "Убедитесь, что при отправке запроса на удаление поста этот пост"
            " удаляется из базы данных."
        )

    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ):
        return (
            "Убедитесь, что при отправке запроса на удаление поста"
            f" {by_user} он перенаправляется на главную страницу."
        )

    def status_error_message(self, by_user: str) -> str:
        return (
            "Убедитесь, что при отправке запроса на удаление публикации"
            f" {by_user} не возникает ошибок."
        )

    @property
    def nonexistent_obj_error_message(self):
        return (
            "Убедитесь, что если авторизованный пользователь отправит запрос к"
            " странице удаления несуществующей публикации, то в ответ он"
            " получит ошибку 404."
        )
