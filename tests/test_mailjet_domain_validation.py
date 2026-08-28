import subscription_api as api


def test_mailjet_validation_file_is_empty_and_not_captured_as_subscription():
    response = api.app.test_client().get(
        "/b326312b921b70e44f45b5cd9e25e7e1.txt",
        headers={"Host": "arccnet.space"},
    )

    assert response.status_code == 200
    assert response.data == b""
    assert response.content_type.startswith("text/plain")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
