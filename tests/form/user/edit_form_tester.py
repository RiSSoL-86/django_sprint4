from form.user.form_tester import UserFormTester


class EditUserFormTester(UserFormTester):

    @property
    def of_which_action(self):
        return 'редактирования'
