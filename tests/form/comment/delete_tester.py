from form.delete_tester import DeleteTester


class DeleteCommentTester(DeleteTester):

    @property
    def one_and_only_one(self):
        return 'один и только один'

    @property
    def which_obj(self):
        return 'комментарий'

    @property
    def of_which_obj(self):
        return 'комментария'

    @property
    def redirect_to_page(self):
        return 'страницу публикации'
