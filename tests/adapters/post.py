from inspect import isclass
from typing import Type

from django.db import models
from django.db.models import Model

from adapters.student_adapter import StudentModelAdapter


class PostModelAdapter(StudentModelAdapter):
    """
    Usage:
    #  With class:
    class_adapter = ModelAdapter(Post)
    class_adapter.image  # gets the ImageField field
                         # of the Post class

    #  With instance:
    item_adapter = CommentAdapter(Post())
    item_adapter.image  # gets the ImageField field
                       # of the Post instance
    """

    @property
    def _access_by_name_fields(self):
        return [
            "id",
            "created_at",
            "is_published",
            "title",
            "text",
            "pub_date",
            "author",
            "category",
            "location",
            "refresh_from_db",
        ]

    @property
    def AdapterFields(self) -> type:
        class _AdapterFields:
            image = models.ImageField()

            field_description = {
                "image": "служит для хранения изображения публикации",
            }

        return _AdapterFields

    @property
    def ItemModel(self) -> Type[Model]:
        from blog.models import Post

        return Post

    @property
    def displayed_field_name_or_value(self):
        """Gets the field name (if `self` is class adapter) or its value
        (if `self` is item adapter) that is displayed on a page"""
        if isclass(self._item_or_cls):
            return "title"
        else:
            return self.title.replace("\n", "")
