from app.modules.ingestion.pipeline import build_wiki_page_url


def test_build_wiki_page_url_escapes_special_title_characters() -> None:
    url = build_wiki_page_url(
        "https://deepwoken.fandom.com/api.php",
        "Duke Erisia? Phase #2",
    )

    assert url == "https://deepwoken.fandom.com/wiki/Duke_Erisia%3F_Phase_%232"
