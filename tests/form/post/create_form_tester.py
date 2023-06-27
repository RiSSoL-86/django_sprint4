from form.post.form_tester import PostFormTester


class CreatePostFormTester(PostFormTester):

    @property
    def of_which_action(self):
        return 'создания'
