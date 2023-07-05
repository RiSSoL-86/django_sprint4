from typing import Type

import pytest
from django.db.models import Model
from mixer.backend.django import Mixer

from fixtures.types import CommentModelAdapterT


@pytest.fixture
def comment(
    mixer: Mixer,
    user: object,
    CommentModel: type,
    CommentModelAdapter: CommentModelAdapterT,
) -> CommentModelAdapterT:
    comment = mixer.blend(f"blog.{CommentModel.__name__}")
    adapted = CommentModelAdapter(comment)
    return adapted


@pytest.fixture
def comment_to_a_post(
    mixer: Mixer,
    post_with_published_location: Model,
    CommentModel: Type[Model],
    CommentModelAdapter: CommentModelAdapterT,
):
    comment_model_name = CommentModel.__name__
    post_field_name = CommentModelAdapter(CommentModel).post.field.name
    mixer_kwargs = {post_field_name: post_with_published_location}
    return mixer.blend(f"blog.{comment_model_name}", **mixer_kwargs)
