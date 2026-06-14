from app.main import app


def route_paths() -> set[str]:
    return {
        path
        for route in app.routes
        if isinstance(path := getattr(route, "path", None), str)
    }


def test_ingestion_category_route_exists() -> None:
    paths = route_paths()
    assert "/api/ingestion/category/{category}" in paths


def test_ingestion_page_route_accepts_titles_with_slashes() -> None:
    paths = route_paths()
    assert "/api/ingestion/pages/{title:path}" in paths
