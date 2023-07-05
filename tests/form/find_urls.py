from typing import List, Sequence, Dict, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag, SoupStrainer

from conftest import KeyVal


def find_links_between_lines(
    page_content: str,
    urls_start_with: str,
    start_lineix: int,
    end_lineix: int,
    link_text_in: Optional[str] = None,
) -> List[Tag]:
    if not link_text_in:
        link_text_in = "\n".join(
            page_content.split("\n")[
                (start_lineix if start_lineix >= 0 else 0): (
                    end_lineix if end_lineix >= 0 else None
                )
            ]
        )
    result_links = []
    link_soup = BeautifulSoup(
        page_content, features="html.parser", parse_only=SoupStrainer("a")
    )
    link: Tag
    for link in link_soup:
        if (
            link.get("href")
            and (
                link.text in link_text_in
                and link.get("href").startswith(urls_start_with)
            )
            and (link.sourceline >= start_lineix or start_lineix < 0)
            and (link.sourceline <= end_lineix or end_lineix < 0)
        ):
            result_links.append(link)
    return result_links


def get_url_display_names(
    urls_start_with: KeyVal, item_id: int, link_tags: Sequence[Tag]
) -> Dict[str, str]:
    """Map urls to their generic form (e.g.
    /post/<post_id>/comment_edit/<comment_id>/)"""
    result = {}

    def get_url_template(url: str) -> str:
        return url.replace(urls_start_with.val, urls_start_with.key).replace(
            f"{item_id}", "<comment_id>"
        )

    for i in range(len(link_tags)):
        url = link_tags[i].get("href")
        result[url] = get_url_template(url)
    return result
