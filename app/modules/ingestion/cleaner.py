import hashlib
import re

from bs4 import BeautifulSoup, Tag


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    _remove_elements(soup)

    text = _extract_text(soup)

    text = _normalize_text(text)

    return text.strip()


def _remove_elements(soup: BeautifulSoup) -> None:
    selectors = [
        "script",
        "style",
        "noscript",
        "iframe",
        ".navbox",
        ".navbar",
        ".nav",
        ".sidebar",
        ".footer",
        ".footernav",
        ".printfooter",
        ".noprint",
        ".mw-empty-elt",
        ".toc",
        "#toc",
        ".mw-editsection",
        ".sidenav",
        ".dropdown-menu",
        ".advertisement",
        ".ads",
        ".ad",
        ".reference",
        ".references",
        "sup.reference",
        "ol.references",
    ]
    for selector in selectors:
        for element in soup.select(selector):
            element.decompose()


def _extract_text(soup: BeautifulSoup) -> str:
    parts: list[str] = []

    body = soup.find("body") or soup.find("div", class_="mw-parser-output") or soup
    root = body if isinstance(body, Tag) else soup

    for element in root.descendants:
        if isinstance(element, Tag):
            tag = element.name
            text = element.get_text(strip=True)
            if not text:
                continue

            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(tag[1])
                prefix = "#" * level
                parts.append(f"{prefix} {text}")
            elif tag == "li":
                parts.append(f"- {text}")
            elif tag in ("p", "td", "th"):
                parts.append(text)
            elif tag in ("table",):
                parts.append(f"[table: {text[:100]}]")
            elif tag in ("br", "hr"):
                parts.append("")

    return "\n\n".join(parts)


def _normalize_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\[edit\]", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    return text.strip()


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
