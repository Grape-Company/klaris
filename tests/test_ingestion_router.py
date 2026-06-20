from app.main import app


def route_paths() -> set[str]:
    paths: set[str] = set()
    for route in app.routes:
        if isinstance(path := getattr(route, "path", None), str):
            paths.add(path)
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            paths.update(
                child_path
                for child_route in original_router.routes
                if isinstance(child_path := getattr(child_route, "path", None), str)
            )
    return paths


def test_ingestion_category_route_exists() -> None:
    paths = route_paths()
    assert "/api/ingestion/category/{category}" in paths


def test_ingestion_page_route_accepts_titles_with_slashes() -> None:
    paths = route_paths()
    assert "/api/ingestion/pages/{title:path}" in paths
