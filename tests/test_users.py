import inspect
import os
from http import HTTPStatus
from pathlib import Path
from typing import Tuple, Set, Optional

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.http import HttpResponse
from django.urls import URLPattern, URLResolver, get_resolver

from adapters.user import UserModelAdapter
from conftest import KeyVal, squash_code
from form.find_urls import find_links_between_lines
from form.user.edit_form_tester import EditUserFormTester
from test_edit import _test_edit


class ManageProfileLinksException(Exception):
    ...


@pytest.mark.django_db
def test_custom_err_handlers(client):
    try:
        from blogicum import urls as blogicum_urls
    except Exception:
        raise AssertionError(
            "Убедитесь, в головном файле с маршрутами нет ошибок."
        )
    urls_src_squashed = squash_code(inspect.getsource(blogicum_urls))
    if "django.contrib.auth.urls" not in urls_src_squashed:
        raise AssertionError(
            "Убедитесь, что подключены маршруты для работы с пользователями из"
            " `django.contrib.auth.urls`."
        )

    def search_url_patterns(substring):
        resolver = get_resolver()
        results = []

        def search_patterns(head, patterns):
            for pattern in patterns:
                if isinstance(pattern, URLPattern):
                    pattern_as_str = head + str(pattern.pattern)
                    if substring in pattern_as_str:
                        results.append(pattern)
                elif isinstance(pattern, URLResolver):
                    search_patterns(
                        head + str(pattern.pattern), pattern.url_patterns
                    )
            return results

        search_patterns(head="", patterns=resolver.url_patterns)

        return results

    registration_url = "auth/registration/"
    auth_registration_patterns = search_url_patterns(registration_url)
    assert auth_registration_patterns, (
        "Убедитесь, что в головном файле с маршрутами переопределён маршрут"
        f" `{registration_url}`."
    )

    auth_templates = {
        "logged_out.html",
        "login.html",
        "password_change_done.html",
        "password_change_form.html",
        "password_reset_complete.html",
        "password_reset_confirm.html",
        "password_reset_done.html",
        "password_reset_form.html",
        "registration_form.html",
    }
    for template in auth_templates:
        fpath: Path = settings.TEMPLATES_DIR / "registration" / template
        frpath: Path = fpath.relative_to(settings.BASE_DIR)
        assert os.path.isfile(
            fpath.resolve()
        ), f"Убедитесь, что файл шаблона `{frpath}` существует."


@pytest.mark.django_db
def test_profile(
        user, another_user, user_client, another_user_client, unlogged_client
):
    user_url = f"/profile/{user.username}/"
    printed_url = "/profile/<username>/"

    User = get_user_model()
    status_code_not_404_err_msg = (
        "Убедитесь, что при обращении к странице несуществующего "
        "пользователя возвращается статус 404."
    )
    try:
        response = user_client.get("/profile/this_is_unexisting_user_name/")
    except User.DoesNotExist:
        raise AssertionError(status_code_not_404_err_msg)

    assert response.status_code == HTTPStatus.NOT_FOUND, (
        status_code_not_404_err_msg)

    user_response: HttpResponse = user_client.get(user_url)

    user_content = user_response.content.decode("utf-8")

    anothers_same_page_response: HttpResponse = another_user_client.get(
        user_url
    )
    anothers_same_page_content = anothers_same_page_response.content.decode(
        "utf-8"
    )

    unlogged_same_page_response: HttpResponse = unlogged_client.get(user_url)
    unlogged_same_page_content = unlogged_same_page_response.content.decode(
        "utf-8"
    )

    for profile_user, profile_user_content in (
            (user, user_content),
            (user, unlogged_same_page_content),
            (user, anothers_same_page_content),
    ):
        _test_user_info_displayed(
            profile_user, profile_user_content, printed_url
        )

    try:
        edit_url, change_pwd_url = try_get_profile_manage_urls(
            user_content, anothers_same_page_content, ignore_urls={user_url}
        )
    except ManageProfileLinksException:
        raise AssertionError(
            "Убедитесь, что на странице профиля пользователя ссылки для"
            " редактирования профиля и изменения пароля видны только владельцу"
            " профиля, но не другим пользователям."
        )

    unlogged_diff_urls = get_extra_urls(
        base_content=unlogged_same_page_content, extra_content=user_content
    )

    assert {edit_url, change_pwd_url}.issubset(set(unlogged_diff_urls)), (
        "Убедитесь, что неаутентифицированному пользователю недоступны ссылки"
        " для редактирования профиля и изменения пароля."
    )

    item_to_edit = user
    item_to_edit_adapter = UserModelAdapter(item_to_edit)
    old_prop_value = item_to_edit_adapter.displayed_field_name_or_value
    update_props = {
        item_to_edit_adapter.item_cls_adapter.displayed_field_name_or_value: (
            f"{old_prop_value} edited"
        )
    }
    _test_edit(
        KeyVal(edit_url, edit_url),
        UserModelAdapter,
        user,
        EditFormTester=EditUserFormTester,
        user_client=user_client,
        unlogged_client=unlogged_client,
        **update_props,
    )


def _test_user_info_displayed(
        profile_user: Model, profile_user_content: str, printed_url: str
) -> None:
    if profile_user.first_name not in profile_user_content:
        raise AssertionError(
            f"Убедитесь, что на странице `{printed_url}` отображается имя"
            " пользователя."
        )
    if profile_user.last_name not in profile_user_content:
        raise AssertionError(
            f"Убедитесь, что на странице `{printed_url}` отображается фамилия"
            " пользователя."
        )


def try_get_profile_manage_urls(
        user_content: str, anothers_page_content: str, ignore_urls: Set[str]
) -> Tuple[str, str]:
    diff_urls = get_extra_urls(
        base_content=anothers_page_content,
        extra_content=user_content,
        ignore_urls=ignore_urls,
    )
    if len(diff_urls) != 2:
        raise ManageProfileLinksException

    # swap variables if needed
    edit_url, change_pwd_url = diff_urls
    change_pwd_marker = "/auth/password_change/"
    if change_pwd_marker in edit_url:
        edit_url, change_pwd_url = change_pwd_url, edit_url
    if change_pwd_marker not in change_pwd_url:
        raise AssertionError(
            "Убедитесь, что на странице профиля владельцу этого профиля"
            f" доступна ссылка `{change_pwd_marker}` для изменения пароля."
        )

    return edit_url, change_pwd_url


def get_extra_urls(
        base_content: str,
        extra_content: str,
        ignore_urls: Optional[Set[str]] = None,
):
    ignore_urls = ignore_urls or set()
    find_links_kwargs = dict(
        urls_start_with="", start_lineix=-1, end_lineix=-1
    )
    user_links = set(
        find_links_between_lines(extra_content, **find_links_kwargs)
    )
    anothers_page_links = set(
        find_links_between_lines(base_content, **find_links_kwargs)
    )
    diff_urls = [
        x.get("href")
        for x in (user_links - anothers_page_links)
        if x.get("href") not in ignore_urls
    ]
    return diff_urls
