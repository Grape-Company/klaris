from app.main import app


def test_ingestion_category_route_exists() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/ingestion/category/{category}" in paths
