from form.comment.form_tester import CommentFormTester


class EditCommentFormTester(CommentFormTester):

    @property
    def of_which_action(self):
        return 'редактирования'
