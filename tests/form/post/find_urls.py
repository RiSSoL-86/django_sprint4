import re
from typing import Tuple

from django.http import HttpResponse

from adapters.post import PostModelAdapter
from fixtures.types import CommentModelAdapterT
from form.find_urls import find_links_between_lines, get_url_display_names
from conftest import KeyVal


def find_edit_and_delete_urls(
    post_adapter: PostModelAdapter,
    comment_adapter: CommentModelAdapterT,
    post_page_response: HttpResponse,
    urls_start_with: KeyVal,
) -> Tuple[KeyVal, KeyVal]:
    """Looks up two links in the post_page_response's content.
    The links must be found between the post's text and the first
    comment to the post.
    The one with the word `edit` in it is for editing the post,
    the other one, therefore, is for its deletion.
    !!! Make posts and comments have unique texts and titles.
    """

    post_page_content = post_page_response.content.decode("utf-8")

    links_not_found_err_msg = (
        "Убедитесь, что на странице поста отображаются комментарии к нему."
        " Проверьте, что автору поста доступны ссылки для редактирования и"
        " для удаления этого поста. Адрес ссылок должен начинаться с"
        f" {urls_start_with.key}"
    )

    # Get info about html between two consecutive posts
    displayed_post_text = post_adapter.displayed_field_name_or_value
    displayed_comment_text = comment_adapter.displayed_field_name_or_value
    pattern = re.compile(
        rf"{displayed_post_text}([\w\W]*?){displayed_comment_text}"
    )
    between_posts_match = pattern.search(post_page_content)
    assert between_posts_match, links_not_found_err_msg
    text_between_posts = between_posts_match.group(1)
    between_posts_start_lineix = post_page_content.count(
        "\n", 0, between_posts_match.start()
    )
    between_posts_end_lineix = between_posts_start_lineix + (
        between_posts_match.group().count("\n")
    )

    post_links = find_links_between_lines(
        post_page_content,
        urls_start_with.val,
        between_posts_start_lineix,
        between_posts_end_lineix,
        link_text_in=text_between_posts,
    )
    if len(set(link.get("href") for link in post_links)) != 2:
        raise AssertionError(links_not_found_err_msg)

    # We have two links. Which one of them is the edit link,
    # and which - the delete link? Edit link must lead to a form.

    edit_link, del_link = post_links[0], post_links[1]
    if "edit" in edit_link.get("href"):
        assert "edit" not in del_link.get(
            "href"
        ), "Убедитесь, что в адресе страницы удаления поста нет слова `edit`."
    elif "edit" in del_link.get("href"):
        edit_link, del_link = del_link, edit_link
    else:
        raise AssertionError(
            "Убедитесь, что адрес страницы редактирования поста"
            " -`posts/<post_id>/edit/`."
        )

    post_url_display_names = get_url_display_names(
        urls_start_with, post_adapter.id, post_links
    )
    edit_url = edit_link.get("href")
    del_url = del_link.get("href")
    return (
        KeyVal(key=edit_url, val=post_url_display_names[edit_url]),
        KeyVal(key=del_url, val=post_url_display_names[del_url]),
    )
