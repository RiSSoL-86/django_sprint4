from typing import TypeVar, Union

from adapters.post import PostModelAdapter
from adapters.user import UserModelAdapter

CommentModelAdapterT = TypeVar("CommentModelAdapterT", bound=type)
ModelAdapterT = Union[CommentModelAdapterT, PostModelAdapter, UserModelAdapter]
