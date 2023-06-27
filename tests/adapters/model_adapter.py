from abc import abstractmethod, ABC
from inspect import isclass
from typing import Union, Type, Any

from django.db.models import Model


class ModelAdapter(ABC):
    """
    Provides an adapter class wrap around student's Model or Model instance.
    It is needed since the attribute names in Model classes are not known,
    and we cannot access them directly.
    This wrapper allows to access field directly by names, performing necessary
    routing and checks (this is done in the descendants of the class).
    """

    def __init__(self, item_or_class: Union[Model, Type[Model]]):
        self._item_or_cls = item_or_class

    def __getattr__(self, name: str) -> Any:
        return getattr(self._item_or_cls, name)

    def get_student_field_name(self, field_name: str) -> str:
        return getattr(self.item_cls_adapter, field_name).field.name

    @property
    @abstractmethod
    def displayed_field_name_or_value(self):
        """Gets the field name (if `self` is class adapter) or its value
        (if `self` is item adapter) that is displayed on a page"""
        ...

    @property
    def item_cls(self):
        if isclass(self._item_or_cls):
            return self._item_or_cls
        else:
            return self._item_or_cls.__class__

    @property
    def item_cls_adapter(self):
        if isclass(self._item_or_cls):
            return self
        else:
            return self.__class__(self._item_or_cls.__class__)
