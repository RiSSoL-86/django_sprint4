from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Optional, Union

from django.db.models import Model
from django.test import Client

from conftest import TitledUrlRepr
from fixtures.types import ModelAdapterT


class BaseTester(ABC):
    @abstractmethod
    def redirect_error_message(
        self, by_user: str, redirect_to_page: Union[TitledUrlRepr, str]
    ):
        raise NotImplementedError

    @abstractmethod
    def status_error_message(self, by_user: str) -> str:
        raise NotImplementedError

    def __init__(
        self,
        model_cls: Type[Model],
        user_client: Client,
        another_user_client: Optional[Client] = None,
        unlogged_client: Optional[Client] = None,
        item_adapter: ModelAdapterT = None,
    ):
        self.user_client = user_client
        self.another_user_client = another_user_client
        self.unlogged_client = unlogged_client
        if item_adapter:
            assert model_cls is item_adapter.item_cls
        self._model_cls = model_cls
        self._item_adapter = item_adapter
