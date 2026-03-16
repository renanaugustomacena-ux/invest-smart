"""Real integration tests for moneymaker_common.grpc_credentials.

Tests TLS configuration from real environment variables and credential loading
from real PEM files on the filesystem. Uses grpc library for actual credential
creation where possible.

NO MOCKS: Uses tempfile for real PEM files and monkeypatch for real env vars.
"""

import pytest

from moneymaker_common.grpc_credentials import (
    _is_production,
    get_tls_config_from_env,
    load_credentials_from_files,
    load_server_credentials,
)

# ------------------------------------------------------------------
# Self-signed PEM content for testing
# ------------------------------------------------------------------

# These are structurally valid PEM blocks. They are NOT cryptographically
# meaningful certificates — they are used to exercise file-reading and
# PEM-parsing paths in grpc.ssl_channel_credentials / ssl_server_credentials.
# grpc accepts any bytes as root_certificates/private_key/certificate_chain;
# it only validates them at connection time, not at credential-creation time.

_DUMMY_CA_CERT_PEM = b"""\
-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJALRiMLAh3nOSMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RjYTAeFw0yNTAxMDEwMDAwMDBaFw0yNjAxMDEwMDAwMDBaMBExDzANBgNVBAMM
BnRlc3RjYTBcMA0GCSqGSIb3DQEBAQUAA0sAMEgCQQC7o96VEPmSkzmjBfFKpVmJ
4BDMJBFYPvahFSjTSHnGKzabsPGm3GV2sBJjPVfzjMTrgqaKRau+UPZMiaF9AcPN
AgMBAAGjUzBRMB0GA1UdDgQWBBQzNfGKPHcw/dummy/base64/padding==
-----END CERTIFICATE-----
"""

_DUMMY_SERVER_CERT_PEM = b"""\
-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJALRiMLAh3nOTMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RjYTAeFw0yNTAxMDEwMDAwMDBaFw0yNjAxMDEwMDAwMDBaMBMxETAPBgNVBAMM
CHRlc3RzcnYwXDANBgkqhkiG9w0BAQEFAANLADBIAkEAu6PelRD5kpM5owXxSqVZ
ieAQzCQRWD72oRUo00h5xis2m7DxptxldrASYz1X84zE64KmikWrvlD2TImhfQHD
zQIDAQABo1MwUTAdBgNVHQ4EFgQUMzXxijx3MP/dummy/server/pad==
-----END CERTIFICATE-----
"""

_DUMMY_SERVER_KEY_PEM = b"""\
-----BEGIN RSA PRIVATE KEY-----
MIIBogIBAAJBALuj3pUQ+ZKTOaMF8UqlWYngEMwkEVg+9qEVKNNIecYrNpuw8abc
dXawEmM9V/OMxOuCpopFq75Q9kyJoX0Bw80CAwEAAQJAFake+private+key+data
for+testing+only+not+a+real+RSA+key+just+filler+bytes+to+make+PEM+
valid+structurally+padding+data+here+for+length+requirements+ok==
-----END RSA PRIVATE KEY-----
"""

_DUMMY_CLIENT_CERT_PEM = b"""\
-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJALRiMLAh3nOUMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl
c3RjYTAeFw0yNTAxMDEwMDAwMDBaFw0yNjAxMDEwMDAwMDBaMBQxEjAQBgNVBAMM
CXRlc3RjbGllMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALuj3pUQ+ZKTOaMF8Uql
WYngEMwkEVg+9qEVKNNIecYrNpuw8abcdXawEmM9V/OMxOuCpopFq75Q9kyJoX0B
w80CAwEAAaNTMFEwHQYDVR0OBBYEFDummy/client/cert/padding==
-----END CERTIFICATE-----
"""

_DUMMY_CLIENT_KEY_PEM = b"""\
-----BEGIN RSA PRIVATE KEY-----
MIIBogIBAAJBALuj3pUQ+ZKTOaMF8UqlWYngEMwkEVg+9qEVKNNIecYrNpuw8abc
dXawEmM9V/OMxOuCpopFq75Q9kyJoX0Bw80CAwEAAQJAClientKeyFakeData+not
real+just+for+structure+testing+filler+bytes+to+make+the+PEM+block+
look+valid+for+file+reading+tests+only+padding+data+here+ok+end==
-----END RSA PRIVATE KEY-----
"""


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def tls_dir(tmp_path):
    """Create a temp directory with real PEM files for TLS testing."""
    ca_file = tmp_path / "ca.crt"
    server_cert_file = tmp_path / "server.crt"
    server_key_file = tmp_path / "server.key"
    client_cert_file = tmp_path / "client.crt"
    client_key_file = tmp_path / "client.key"

    ca_file.write_bytes(_DUMMY_CA_CERT_PEM)
    server_cert_file.write_bytes(_DUMMY_SERVER_CERT_PEM)
    server_key_file.write_bytes(_DUMMY_SERVER_KEY_PEM)
    client_cert_file.write_bytes(_DUMMY_CLIENT_CERT_PEM)
    client_key_file.write_bytes(_DUMMY_CLIENT_KEY_PEM)

    return tmp_path


@pytest.fixture()
def clean_tls_env(monkeypatch):
    """Remove all MONEYMAKER_TLS_* and MONEYMAKER_ENV env vars for a clean slate."""
    for var in [
        "MONEYMAKER_TLS_ENABLED",
        "MONEYMAKER_TLS_CA_CERT",
        "MONEYMAKER_TLS_CLIENT_CERT",
        "MONEYMAKER_TLS_CLIENT_KEY",
        "MONEYMAKER_TLS_SERVER_CERT",
        "MONEYMAKER_TLS_SERVER_KEY",
        "MONEYMAKER_ENV",
    ]:
        monkeypatch.delenv(var, raising=False)


# ------------------------------------------------------------------
# get_tls_config_from_env — real env vars
# ------------------------------------------------------------------


class TestGetTlsConfigFromEnv:
    """Test get_tls_config_from_env reading real environment variables."""

    def test_defaults_tls_disabled(self, clean_tls_env):
        """With no env vars set, TLS is disabled with default paths."""
        config = get_tls_config_from_env()
        assert config["enabled"] is False
        assert config["ca_cert"] == "/etc/ssl/certs/ca.crt"
        assert config["client_cert"] == ""
        assert config["client_key"] == ""
        assert config["server_cert"] == ""
        assert config["server_key"] == ""

    def test_tls_enabled_true(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "true")
        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_1(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "1")
        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_yes(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "yes")
        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_false_string(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "false")
        config = get_tls_config_from_env()
        assert config["enabled"] is False

    def test_tls_enabled_uppercase_true(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "TRUE")
        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_custom_paths(self, clean_tls_env, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "true")
        monkeypatch.setenv("MONEYMAKER_TLS_CA_CERT", "/custom/ca.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_CLIENT_CERT", "/custom/client.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_CLIENT_KEY", "/custom/client.key")
        monkeypatch.setenv("MONEYMAKER_TLS_SERVER_CERT", "/custom/server.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_SERVER_KEY", "/custom/server.key")
        config = get_tls_config_from_env()
        assert config["enabled"] is True
        assert config["ca_cert"] == "/custom/ca.crt"
        assert config["client_cert"] == "/custom/client.crt"
        assert config["client_key"] == "/custom/client.key"
        assert config["server_cert"] == "/custom/server.crt"
        assert config["server_key"] == "/custom/server.key"


# ------------------------------------------------------------------
# _is_production — real env vars
# ------------------------------------------------------------------


class TestIsProduction:
    """Test _is_production reads from real MONEYMAKER_ENV env var."""

    def test_production(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        assert _is_production() is True

    def test_prod(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "prod")
        assert _is_production() is True

    def test_development(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        assert _is_production() is False

    def test_empty(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        assert _is_production() is False

    def test_staging(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "staging")
        assert _is_production() is False

    def test_case_insensitive_production(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "PRODUCTION")
        assert _is_production() is True


# ------------------------------------------------------------------
# load_credentials_from_files — real PEM files
# ------------------------------------------------------------------


class TestLoadCredentialsFromFiles:
    """Test load_credentials_from_files with real PEM files on disk."""

    def test_simple_tls_ca_only(self, tls_dir):
        """Simple TLS: load only the CA certificate from a real file."""
        ca_path = str(tls_dir / "ca.crt")
        credentials = load_credentials_from_files(ca_cert_path=ca_path)
        # grpc.ssl_channel_credentials returns a ChannelCredentials object
        assert credentials is not None

    def test_mtls_all_files(self, tls_dir):
        """mTLS: load CA, client cert, and client key from real files."""
        credentials = load_credentials_from_files(
            ca_cert_path=str(tls_dir / "ca.crt"),
            client_cert_path=str(tls_dir / "client.crt"),
            client_key_path=str(tls_dir / "client.key"),
        )
        assert credentials is not None

    def test_missing_ca_cert_raises_file_not_found(self, tmp_path):
        """FileNotFoundError when the CA cert file does not exist."""
        nonexistent = str(tmp_path / "nonexistent_ca.crt")
        with pytest.raises(FileNotFoundError, match="CA certificate"):
            load_credentials_from_files(ca_cert_path=nonexistent)

    def test_missing_client_cert_raises_file_not_found(self, tls_dir):
        """FileNotFoundError when client cert does not exist but key does."""
        missing_cert = str(tls_dir / "missing_client.crt")
        with pytest.raises(FileNotFoundError, match="Client certificate"):
            load_credentials_from_files(
                ca_cert_path=str(tls_dir / "ca.crt"),
                client_cert_path=missing_cert,
                client_key_path=str(tls_dir / "client.key"),
            )

    def test_missing_client_key_raises_file_not_found(self, tls_dir):
        """FileNotFoundError when client key does not exist but cert does."""
        missing_key = str(tls_dir / "missing_client.key")
        with pytest.raises(FileNotFoundError, match="Client key"):
            load_credentials_from_files(
                ca_cert_path=str(tls_dir / "ca.crt"),
                client_cert_path=str(tls_dir / "client.crt"),
                client_key_path=missing_key,
            )

    def test_cert_without_key_raises_value_error(self, tls_dir):
        """ValueError when client_cert is provided without client_key."""
        with pytest.raises(ValueError, match="insieme"):
            load_credentials_from_files(
                ca_cert_path=str(tls_dir / "ca.crt"),
                client_cert_path=str(tls_dir / "client.crt"),
                client_key_path=None,
            )

    def test_key_without_cert_raises_value_error(self, tls_dir):
        """ValueError when client_key is provided without client_cert."""
        with pytest.raises(ValueError, match="insieme"):
            load_credentials_from_files(
                ca_cert_path=str(tls_dir / "ca.crt"),
                client_cert_path=None,
                client_key_path=str(tls_dir / "client.key"),
            )

    def test_file_content_is_actually_read(self, tls_dir):
        """Confirm that the PEM bytes are actually read from the real files."""
        ca_path = tls_dir / "ca.crt"
        # Verify the file actually has content
        content = ca_path.read_bytes()
        assert b"BEGIN CERTIFICATE" in content
        assert len(content) > 100

        # The function should succeed (it reads this real file)
        credentials = load_credentials_from_files(ca_cert_path=str(ca_path))
        assert credentials is not None


# ------------------------------------------------------------------
# load_server_credentials — real PEM files
# ------------------------------------------------------------------


class TestLoadServerCredentials:
    """Test load_server_credentials with real PEM files on disk."""

    def test_server_credentials_with_client_auth(self, tls_dir):
        """Load server credentials with mTLS (require_client_cert=True)."""
        credentials = load_server_credentials(
            ca_cert_path=str(tls_dir / "ca.crt"),
            server_cert_path=str(tls_dir / "server.crt"),
            server_key_path=str(tls_dir / "server.key"),
            require_client_cert=True,
        )
        assert credentials is not None

    def test_server_credentials_without_client_auth(self, tls_dir):
        """Load server credentials with TLS only (require_client_cert=False)."""
        credentials = load_server_credentials(
            ca_cert_path=str(tls_dir / "ca.crt"),
            server_cert_path=str(tls_dir / "server.crt"),
            server_key_path=str(tls_dir / "server.key"),
            require_client_cert=False,
        )
        assert credentials is not None

    def test_missing_ca_raises(self, tls_dir):
        """FileNotFoundError when CA cert is missing."""
        with pytest.raises(FileNotFoundError, match="CA certificate"):
            load_server_credentials(
                ca_cert_path=str(tls_dir / "missing_ca.crt"),
                server_cert_path=str(tls_dir / "server.crt"),
                server_key_path=str(tls_dir / "server.key"),
            )

    def test_missing_server_cert_raises(self, tls_dir):
        """FileNotFoundError when server cert is missing."""
        with pytest.raises(FileNotFoundError, match="Server certificate"):
            load_server_credentials(
                ca_cert_path=str(tls_dir / "ca.crt"),
                server_cert_path=str(tls_dir / "missing_server.crt"),
                server_key_path=str(tls_dir / "server.key"),
            )

    def test_missing_server_key_raises(self, tls_dir):
        """FileNotFoundError when server key is missing."""
        with pytest.raises(FileNotFoundError, match="Server key"):
            load_server_credentials(
                ca_cert_path=str(tls_dir / "ca.crt"),
                server_cert_path=str(tls_dir / "server.crt"),
                server_key_path=str(tls_dir / "missing_server.key"),
            )
