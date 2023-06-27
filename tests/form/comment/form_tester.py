from form.base_form_tester import BaseFormTester


class CommentFormTester(BaseFormTester):

    @property
    def has_textarea(self):
        return True

    @property
    def one_and_only_one(self):
        return 'один и только один'

    @property
    def which_obj(self):
        return 'комментарий'

    @property
    def of_which_obj(self):
        return 'комментария'
