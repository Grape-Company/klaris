from app.modules.ingestion.cleaner import clean_html, compute_content_hash


def test_clean_html_removes_scripts() -> None:
    html = "<html><body><script>alert('xss')</script><p>Hello</p></body></html>"
    result = clean_html(html)
    assert "Hello" in result
    assert "script" not in result


def test_clean_html_preserves_headings() -> None:
    html = "<html><body><h1>Title</h1><h2>Subtitle</h2><p>Text</p></body></html>"
    result = clean_html(html)
    assert "# Title" in result
    assert "## Subtitle" in result


def test_clean_html_removes_nav_elements() -> None:
    html = '<html><body><div class="navbox">nav</div><p>content</p></body></html>'
    result = clean_html(html)
    assert "content" in result
    assert "nav" not in result


def test_clean_html_preserves_infobox_content() -> None:
    html = """
    <html>
      <body>
        <table class="infobox">
          <tr><th>Requirement</th><td>40 Shadowcast</td></tr>
        </table>
        <p>Main content</p>
      </body>
    </html>
    """
    result = clean_html(html)
    assert "Requirement" in result
    assert "40 Shadowcast" in result
    assert "Main content" in result


def test_content_hash_is_deterministic() -> None:
    text = "same content"
    assert compute_content_hash(text) == compute_content_hash(text)


def test_content_hash_changes_with_content() -> None:
    assert compute_content_hash("hello") != compute_content_hash("world")
