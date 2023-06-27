from form.delete_tester import DeleteTester


class DeletePostTester(DeleteTester):

    @property
    def one_and_only_one(self):
        return 'одна и только одна'

    @property
    def which_obj(self):
        return 'публикация'

    @property
    def of_which_obj(self):
        return 'публикации'

    @property
    def redirect_to_page(self):
        return 'главную страницу'
