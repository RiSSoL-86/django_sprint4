from form.base_form_tester import BaseFormTester


class UserFormTester(BaseFormTester):

    @property
    def has_textarea(self):
        return False

    @property
    def one_and_only_one(self):
        return 'один и только один'

    @property
    def which_obj(self):
        return 'профиль пользователя'

    @property
    def of_which_obj(self):
        return 'профиля пользователя'
