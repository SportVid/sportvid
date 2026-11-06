import pytest


@pytest.mark.django_db
def test_healthy_endpoint(client):
    response = client.get("/healthy/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
