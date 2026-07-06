import importlib


def test_generate_blob_storage_token(mocker, monkeypatch):
    """Test generate-blob-storage-token."""
    monkeypatch.setenv("BlobStorageAccountName", "Test123")
    monkeypatch.setenv("BlobStorageAccountKey", "Test123")

    importlib.import_module("generate-blob-storage-token")
