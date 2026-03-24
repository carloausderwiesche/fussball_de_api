import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fussball_api.logo_proxy import download_and_rewrite_logo, _logo_filename


def test_logo_filename_deterministic():
    """Same URL always produces the same filename."""
    url = "https://media.fussball.de/club-logo.png"
    assert _logo_filename(url) == _logo_filename(url)
    assert _logo_filename(url).endswith(".png")


def test_logo_filename_different_urls():
    """Different URLs produce different filenames."""
    assert _logo_filename("https://a.png") != _logo_filename("https://b.png")


def test_download_and_rewrite_logo_empty_url():
    """Empty URL returns empty string."""
    assert download_and_rewrite_logo("") == ""


def test_download_and_rewrite_logo_existing_file(tmp_path, monkeypatch):
    """If the file already exists, no HTTP call is made."""
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGOS_DIR", tmp_path)
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGO_BASE_URL", "")

    url = "https://media.fussball.de/club-logo.png"
    filename = _logo_filename(url)
    (tmp_path / filename).write_bytes(b"PNG_DATA")

    with patch("fussball_api.logo_proxy.httpx") as mock_httpx:
        result = download_and_rewrite_logo(url)
        mock_httpx.Client.assert_not_called()

    assert result == f"/logos/{filename}"


@patch("fussball_api.logo_proxy.httpx.Client")
def test_download_and_rewrite_logo_new_file(mock_client_cls, tmp_path, monkeypatch):
    """Downloads the file and returns the local path."""
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGOS_DIR", tmp_path)
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGO_BASE_URL", "")

    url = "https://media.fussball.de/new-logo.png"
    filename = _logo_filename(url)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"PNG_DATA"
    mock_client = MagicMock()
    mock_client.__enter__ = lambda self: mock_client
    mock_client.__exit__ = lambda self, *a: None
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    result = download_and_rewrite_logo(url)

    assert result == f"/logos/{filename}"
    assert (tmp_path / filename).read_bytes() == b"PNG_DATA"


@patch("fussball_api.logo_proxy.httpx.Client")
def test_download_and_rewrite_logo_http_failure(mock_client_cls, tmp_path, monkeypatch):
    """On HTTP error, returns original URL as fallback."""
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGOS_DIR", tmp_path)
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGO_BASE_URL", "")

    url = "https://media.fussball.de/fail.png"

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_client = MagicMock()
    mock_client.__enter__ = lambda self: mock_client
    mock_client.__exit__ = lambda self, *a: None
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    result = download_and_rewrite_logo(url)
    assert result == url


@patch("fussball_api.logo_proxy.httpx.Client")
def test_download_and_rewrite_logo_request_error(mock_client_cls, tmp_path, monkeypatch):
    """On network error, returns original URL as fallback."""
    import httpx

    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGOS_DIR", tmp_path)
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGO_BASE_URL", "")

    url = "https://media.fussball.de/error.png"

    mock_client = MagicMock()
    mock_client.__enter__ = lambda self: mock_client
    mock_client.__exit__ = lambda self, *a: None
    mock_client.get.side_effect = httpx.RequestError(
        "timeout", request=httpx.Request("GET", url)
    )
    mock_client_cls.return_value = mock_client

    result = download_and_rewrite_logo(url)
    assert result == url


def test_download_and_rewrite_logo_with_base_url(tmp_path, monkeypatch):
    """LOGO_BASE_URL is prepended to the returned path."""
    monkeypatch.setattr("fussball_api.logo_proxy.settings.LOGOS_DIR", tmp_path)
    monkeypatch.setattr(
        "fussball_api.logo_proxy.settings.LOGO_BASE_URL",
        "https://fussball-de-api.example.de",
    )

    url = "https://media.fussball.de/club-logo.png"
    filename = _logo_filename(url)
    (tmp_path / filename).write_bytes(b"PNG_DATA")

    result = download_and_rewrite_logo(url)
    assert result == f"https://fussball-de-api.example.de/logos/{filename}"
