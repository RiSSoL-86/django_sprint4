from inspect import isclass

from adapters.model_adapter import ModelAdapter


class UserModelAdapter(ModelAdapter):
    @property
    def displayed_field_name_or_value(self):
        """Gets the field name (if `self` is class adapter) or its value
        (if `self` is item adapter) that is displayed on a page"""
        if isclass(self._item_or_cls):
            return "last_name"
        else:
            return self.last_name.replace("\n", "")
