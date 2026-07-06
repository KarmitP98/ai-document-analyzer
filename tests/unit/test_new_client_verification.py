import importlib


def test_new_client_verification_main_should_run(mocker, caplog):
    """Test main should run."""
    mocker.patch("azure.functions.HttpResponse")
    req = mocker.MagicMock()
    json_mock = mocker.patch("json.dumps")
    mocker.patch("new-client-verification.get_auth_key")
    mocker.patch("new-client-verification.get_root_folder_list")
    expected = "Success"

    new_client_verification = importlib.import_module("new-client-verification")
    new_client_verification.main(req)

    assert json_mock.called_once()
    for record in caplog.records:
        assert expected in record
