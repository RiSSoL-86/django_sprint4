import os
import re
import time
from http import HTTPStatus
from inspect import getsource
from pathlib import Path
from typing import (
    Iterable,
    Type,
    Optional,
    Union,
    Any,
    Tuple,
    List,
    NamedTuple,
    TypeVar,
)

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Model, Field
from django.forms import BaseForm
from django.http import HttpResponse
from django.test import override_settings
from django.test.client import Client
from mixer.backend.django import mixer as _mixer

N_PER_FIXTURE = 3
N_PER_PAGE = 10
COMMENT_TEXT_DISPLAY_LEN_FOR_TESTS = 50

KeyVal = NamedTuple("KeyVal", [("key", Optional[str]), ("val", Optional[str])])
UrlRepr = NamedTuple("UrlRepr", [("url", str), ("repr", str)])
TitledUrlRepr = TypeVar("TitledUrlRepr", bound=Tuple[UrlRepr, str])


@pytest.fixture(autouse=True)
def enable_debug_false():
    with override_settings(DEBUG=False):
        yield


class SafeImportFromContextManager:
    def __init__(
            self,
            import_path: str,
            import_names: Iterable[str],
            import_of: str = "",
    ):
        self._import_path: str = import_path
        self._import_names: Iterable[str] = import_names
        self._import_of = f"{import_of} " if import_of else ""

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is ImportError:
            disp_imp_names = "`, ".join(self._import_names)
            raise AssertionError(
                f"Убедитесь, что в файле `{self._import_path}` нет ошибок. "
                f"При импорте из него {self._import_of}"
                f"`{disp_imp_names}` возникла ошибка:\n"
                f"{exc_type.__name__}: {exc_value}"
            )


with SafeImportFromContextManager(
        "blog/models.py", ["Category", "Location", "Post"], import_of="моделей"
):
    try:
        from blog.models import Category, Location, Post  # noqa:F401
    except RuntimeError:
        registered_apps = set(app.name for app in apps.get_app_configs())
        need_apps = {"blog": "blog", "pages": "pages"}
        if not set(need_apps.values()).intersection(registered_apps):
            need_apps = {
                "blog": "blog.apps.BlogConfig",
                "pages": "pages.apps.PagesConfig",
            }

        for need_app_name, need_app_conf_name in need_apps.items():
            if need_app_conf_name not in registered_apps:
                raise AssertionError(
                    "Убедитесь, что зарегистрировано приложение "
                    f"{need_app_name}"
                )

pytest_plugins = [
    "fixtures.posts",
    "fixtures.locations",
    "fixtures.categories",
    "fixtures.comments",
    "adapters.comment",
]


@pytest.fixture
def mixer():
    return _mixer


@pytest.fixture
def user(mixer):
    User = get_user_model()
    user = mixer.blend(User)
    return user


@pytest.fixture
def another_user(mixer):
    User = get_user_model()
    return mixer.blend(User)


@pytest.fixture
def user_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def unlogged_client(client):
    return client


@pytest.fixture
def another_user_client(another_user):
    client = Client()
    client.force_login(another_user)
    return client


def get_post_list_context_key(
        user_client, page_url, page_load_err_msg, key_missing_msg
):
    try:
        post_response = user_client.get(page_url)
    except Exception:
        raise AssertionError(page_load_err_msg)
    assert post_response.status_code == HTTPStatus.OK, page_load_err_msg
    post_list_key = None
    for key, val in dict(post_response.context).items():
        try:
            assert isinstance(iter(val).__next__(), Post)
            post_list_key = key
            break
        except Exception:
            pass
    assert post_list_key, key_missing_msg
    return post_list_key


class _TestModelAttrs:
    @property
    def model(self):
        raise NotImplementedError(
            "Override this property in inherited test class"
        )

    def get_parameter_display_name(self, param: str) -> str:
        return param

    def test_model_attrs(
            self, field: str, type: type, params: dict,
            field_error: Optional[str], type_error: Optional[str],
            param_error: Optional[str], value_error: Optional[str]):
        model_name = self.model.__name__
        field_error = field_error or (
            f"В модели `{model_name}` укажите атрибут `{field}`.")
        assert hasattr(self.model, field), field_error

        model_field = getattr(self.model, field).field
        type_error = type_error or (
            f"В модели `{model_name}` у атрибута `{field}` "
            f"укажите тип `{type}`."
        )
        assert isinstance(model_field, type), type_error

        for param, value_param in params.items():
            display_name = self.get_parameter_display_name(param)
            param_error = param_error or (
                f"В модели `{model_name}` для атрибута `{field}` "
                f"укажите параметр `{display_name}`."
            )
            assert param in model_field.__dict__, param_error

            value_error = value_error or (
                f"В модели `{model_name}` в атрибуте `{field}` "
                f"проверьте значение параметра `{display_name}` "
                "на соответствие заданию."
            )
            assert model_field.__dict__.get(param) == value_param, value_error


@pytest.fixture
def PostModel() -> Type[Model]:
    try:
        from blog.models import Post
    except Exception as e:
        raise AssertionError(
            "При импорте модели `Post` из файла `models.py` возникла ошибка."
            " Убедитесь, что в файле `blog/models.py` нет ошибок и что в нём"
            " объявлена модель Post. Сообщение об"
            f" ошибке:\n{type(e).__name__}: {e}"
        )
    return Post


@pytest.fixture
def CommentModel() -> Model:
    try:
        from blog import models
    except Exception as e:
        raise AssertionError(
            "Убедитесь, что в файле `blog/models.py` нет ошибок. "
            "При импорте `models.py` возникла ошибка:\n"
            f"{type(e).__name__}: {e}"
        )
    models_src_code = getsource(models)
    models_src_clean = re.sub("#.+", "", models_src_code)
    class_defs = re.findall(
        r"(class +\w+[\w\W]+?)(?=class)", models_src_clean + "class"
    )
    comment_class_name = ""
    known_class_names = {"BaseModel", "Meta", "Category", "Location", "Post"}
    for class_def in class_defs:
        class_names = re.findall(
            r"class +(\w+)[\w\W]+ForeignKey[\w\W]+Post", class_def
        )
        for name in class_names:
            if name not in known_class_names:
                comment_class_name = name
                break
        if comment_class_name:
            break
    assert comment_class_name, (
        "Убедитесь, что в файле `blog/models.py` объявлена модель комментария"
        " с полем `ForeignKey`, связывающим её с моделью `Post`."
    )
    return getattr(models, comment_class_name)


class ItemNotCreatedException(Exception):
    ...


def get_get_response_safely(
        user_client: Client, url: str, err_msg: Optional[str] = None,
        expected_status=HTTPStatus.OK
) -> HttpResponse:
    response = user_client.get(url)
    if err_msg is not None:
        assert response.status_code == expected_status, err_msg
    return response


def get_a_post_get_response_safely(
        user_client: Client, post_id: Union[str, int]
) -> HttpResponse:
    return get_get_response_safely(
        user_client,
        url=f"/posts/{post_id}/",
        err_msg=(
            "Убедитесь, что опубликованный пост с опубликованной категорией и"
            " датой публикации в прошлом отображается на странице публикации."
        ),
    )


def get_create_a_post_get_response_safely(user_client: Client) -> HttpResponse:
    url = "/posts/create/"
    return get_get_response_safely(
        user_client,
        url=url,
        err_msg=(
            "Убедитесь, что страница создания публикации по адресу"
            f" {url} отображается без ошибок."
        ),
    )


def _testget_context_item_by_class(
        context, cls: type, err_msg: str, inside_iter: bool = False
) -> KeyVal:
    """If `err_msg` is not empty, empty return value will
    produce an AssertionError with the `err_msg` error message"""

    def is_a_match(val: Any):
        if inside_iter:
            try:
                return isinstance(iter(val).__next__(), cls)
            except Exception:
                return False
        else:
            return isinstance(val, cls)

    matched_keyval: KeyVal = KeyVal(key=None, val=None)
    matched_keyvals: List[KeyVal] = []
    for key, val in dict(context).items():
        if is_a_match(val):
            matched_keyval = KeyVal(key, val)
            matched_keyvals.append(matched_keyval)
    if err_msg:
        assert len(matched_keyvals) == 1, err_msg
        assert matched_keyval.key, err_msg

    return matched_keyval


def _testget_context_item_by_key(context, key: str, err_msg: str) -> KeyVal:
    context_as_dict = dict(context)
    if key not in context_as_dict:
        raise AssertionError(err_msg)
    return KeyVal(key, context_as_dict[key])


def get_page_context_form(user_client: Client, page_url: str) -> KeyVal:
    response = user_client.get(page_url)
    if not str(response.status_code).startswith("2"):
        return KeyVal(key=None, val=None)
    return _testget_context_item_by_class(response.context, BaseForm, "")


def restore_cleaned_data(cleaned_data: dict) -> dict:
    """On validation id values of related fields
    are replaced by correspoinding objects, which fails subsequent validations.
    This function restores related fields back to id values."""
    cleaned_data_fixed = {
        k: v.id if isinstance(v, Model) else v for k, v in cleaned_data.items()
    }
    return cleaned_data_fixed


def squash_code(code: str) -> str:
    result = re.sub(r"#.+", "", code)
    result = result.replace("\n", "").replace(" ", "")
    return result


def get_field_key(field_type: type, field: Field) -> Tuple[str, Optional[str]]:
    if field.is_relation:
        return (field_type.__name__, field.related_model.__name__)
    else:
        return (field_type.__name__, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    start_time = time.time()

    yield

    from blogicum import settings

    image_dir = Path(settings.__file__).parent.parent / settings.MEDIA_ROOT

    for root, dirs, files in os.walk(image_dir):
        for filename in files:
            if (
                    filename.endswith(".jpg")
                    or filename.endswith(".gif")
                    or filename.endswith(".png")
            ):
                file_path = os.path.join(root, filename)
                if os.path.getmtime(file_path) >= start_time:
                    os.remove(file_path)
