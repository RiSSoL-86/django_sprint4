from abc import abstractmethod
from typing import Union, Type, Any

from django.db.models import Model, Field

from adapters.model_adapter import ModelAdapter
from conftest import get_field_key


class StudentModelAdapter(ModelAdapter):
    def __init__(self, item_or_class: Union[Model, Type[Model]]):
        super().__init__(item_or_class=item_or_class)

    @property
    @abstractmethod
    def _access_by_name_fields(self):
        ...

    @property
    @abstractmethod
    def AdapterFields(self) -> type:
        ...

    @property
    @abstractmethod
    def ItemModel(self) -> Type[Model]:
        ...

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name in self._access_by_name_fields:
            return getattr(self._item_or_cls, name)

        item_fields = [
            (f.name, type(f), getattr(self.ItemModel, f.name).field)
            for f in self.ItemModel._meta.concrete_fields
            if issubclass(type(f), Field)
            and (f.name not in self._access_by_name_fields)
        ]

        item_field_names = {
            get_field_key(_type, field): name
            for name, _type, field in item_fields
        }

        assert len(item_field_names) == len(item_fields), (
            f"Убедитесь, что в модели {self.ItemModel.__name__} нет полей,"
            " которые не описаны в задании. Проверьте, что для всех полей"
            " модели правильно заданы типы."
        )

        adapter_field_key = get_field_key(
            type(getattr(self.AdapterFields, name)),
            getattr(self.AdapterFields, name),
        )
        try:
            item_field_name = item_field_names[adapter_field_key]
        except KeyError:
            raise AssertionError(
                f"В модели `{self.ItemModel.__name__}` создайте поле типа"
                f" `{adapter_field_key[0]}`, которое"
                f" {self.AdapterFields.field_description[name]}."
            )
        return getattr(self._item_or_cls, item_field_name)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            self.__dict__[key] = value
            return
        student_key = self.get_student_field_name(key)
        setattr(self._item_or_cls, student_key, value)

    def save(self, *args, **kwargs):
        self._item_or_cls.save(*args, **kwargs)

    @property
    @abstractmethod
    def displayed_field_name_or_value(self):
        ...
