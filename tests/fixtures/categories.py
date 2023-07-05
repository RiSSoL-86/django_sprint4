import pytest
from mixer.backend.django import Mixer


@pytest.fixture
def published_category(mixer: Mixer):
    return mixer.blend("blog.Category", is_published=True)


@pytest.fixture
def another_category(mixer: Mixer):
    return mixer.blend("blog.Category", is_published=True)
