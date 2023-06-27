from form.comment.form_tester import CommentFormTester


class CreateCommentFormTester(CommentFormTester):

    @property
    def of_which_action(self):
        return 'создания'
