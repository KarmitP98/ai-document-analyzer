import importlib


def test_generate_table_storage_token(mocker, monkeypatch):
    """Test generate-table-storage-token."""
    monkeypatch.setenv("BlobStorageAccountName", "Test123")
    monkeypatch.setenv("BlobStorageAccountKey", "Test123")

    importlib.import_module("generate-table-storage-token")
