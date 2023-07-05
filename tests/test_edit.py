from typing import Type, Optional, Dict

import django.test
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Model
from django.forms import BaseForm
from django.http import HttpResponse

from fixtures.types import ModelAdapterT
from form.base_form_tester import BaseFormTester
from conftest import (
    KeyVal,
    get_get_response_safely,
    _testget_context_item_by_class,
)


def _test_edit(
    edit_url_vs_printed_url: KeyVal,
    ModelAdapter: ModelAdapterT,
    item: Model,
    EditFormTester: Type[BaseFormTester],
    user_client: django.test.Client,
    another_user_client: Optional[django.test.Client] = None,
    unlogged_client: Optional[django.test.Client] = None,
    file_data: Optional[Dict[str, SimpleUploadedFile]] = None,
    **update_props
) -> HttpResponse:
    edit_url = edit_url_vs_printed_url.key
    item_adapter = ModelAdapter(item)
    ItemModel = type(item)

    def create_updated_form(**updated_props):
        response = user_client.get(edit_url)
        _, form = _testget_context_item_by_class(
            response.context, BaseForm, ""
        )
        return EditFormTester.init_create_form_from_item(
            item,
            form.__class__,
            ModelAdapter=ModelAdapter,
            file_data=file_data,
            **updated_props
        )

    updated_form = create_updated_form(**update_props)

    response = get_get_response_safely(user_client, edit_url)
    tester = EditFormTester(
        response,
        ItemModel,
        user_client,
        another_user_client,
        unlogged_client,
        ModelAdapter=ModelAdapter,
        item_adapter=item_adapter,
    )
    return tester.test_edit_item(
        updated_form, qs=ItemModel.objects.all(), item_adapter=item_adapter
    )
