import importlib

import pytest


@pytest.mark.skip("This function needs review.")
def test_page_labelling(mocker, monkeypatch):
    """Test page labelling.

    Page labeling is currently hanging because importing azure.data.tables immediately
    accesses certificate and http url.
    """
    monkeypatch.setenv("CV_KEY", "Test123")
    monkeypatch.setenv("CV_ENDPOINT", "Test123")
    monkeypatch.setenv("TA_KEY", "Test123")
    monkeypatch.setenv("TA_ENDPOINT", "Test123")
    monkeypatch.setenv("STORAGE_CONNECTION_STRING", "Test123")
    mocker.patch("page-labelling.DefaultAzureCredential")
    mocker.patch("page-labelling.BlobServiceClient")
    # azure.data.tables.TableClient = mocker.MagicMock()
    # azure.data.tables.UpdateMode = mocker.MagicMock()
    # mocker.patch("builtins.open")
    # mocker.patch("page-labelling.os.remove")
    # mocker.patch("classes.chromadiverse")
    # mocker.patch("page-labelling.ChromaDiverse")
    # mocker.patch("azure.core")
    # mocker.patch("page-labelling.azure.data.tables.TableClient")
    # mocker.patch("page-labelling.TableClient.from_connection_string")
    # mocker.patch("page-labelling.ChromaDiverse.__init__")

    importlib.import_module("page-labelling")
