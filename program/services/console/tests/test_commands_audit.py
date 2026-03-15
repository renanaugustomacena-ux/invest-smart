"""Tests for security audit commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.audit import (
    _audit_compliance,
    _audit_dependencies,
    _audit_docker,
    _audit_env,
    _audit_hashchain,
    _audit_permissions,
    _audit_secrets,
    _audit_security,
    _audit_tls,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestAuditSecurity:
    @patch("moneymaker_console.commands.audit.run_tool")
    def test_security_audit(self, mock_run):
        mock_run.return_value = ""
        result = _audit_security()
        assert "Security Audit" in result

    @patch("moneymaker_console.commands.audit.run_tool")
    def test_with_redis_password(self, mock_run):
        mock_run.return_value = ""
        with patch.dict(os.environ, {"MONEYMAKER_REDIS_PASSWORD": "secret123"}):
            result = _audit_security()
            assert "Redis password configured" in result


class TestAuditSecrets:
    @patch("moneymaker_console.commands.audit.run_tool")
    def test_secrets_clean(self, mock_run):
        mock_run.return_value = ""
        result = _audit_secrets()
        assert "Secret Scan" in result
        assert "CLEAN" in result

    @patch("moneymaker_console.commands.audit.run_tool")
    def test_secrets_found(self, mock_run):
        mock_run.side_effect = lambda cmd, **kw: "file.py" if "sk_live_" in cmd else ""
        result = _audit_secrets()
        assert "Secret Scan" in result


class TestAuditTls:
    def test_no_tls_configured(self):
        result = _audit_tls()
        assert "TLS Audit" in result
        assert "INFO" in result


class TestAuditDependencies:
    @patch("moneymaker_console.commands.audit.run_tool")
    def test_dependencies(self, mock_run):
        mock_run.return_value = "No known vulnerabilities"
        result = _audit_dependencies()
        assert "Dependency" in result


class TestAuditPermissions:
    def test_permissions(self):
        result = _audit_permissions()
        assert "Permission" in result


class TestAuditDocker:
    @patch("moneymaker_console.commands.audit._PROJECT_ROOT")
    def test_no_compose(self, mock_root, tmp_path):
        mock_root.__truediv__ = lambda s, k: tmp_path / k
        result = _audit_docker()
        assert "[error]" in result or "Docker" in result


class TestAuditHashchain:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_with_entries(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (100,)
        mock_cf.get_postgres.return_value = mock_db
        result = _audit_hashchain()
        assert "100" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_no_entries(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (0,)
        mock_cf.get_postgres.return_value = mock_db
        result = _audit_hashchain()
        assert "No audit log" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db error")
        result = _audit_hashchain()
        assert "[error]" in result


class TestAuditCompliance:
    def test_compliance_report(self):
        result = _audit_compliance()
        assert "Compliance" in result


class TestAuditEnv:
    def test_no_env_file(self):
        from pathlib import Path
        with patch("moneymaker_console.commands.config._ENV_FILE", Path("/nonexistent")):
            result = _audit_env()
            assert "warning" in result.lower() or "Environment" in result

    def test_with_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\nAPI_KEY=short\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _audit_env()
            assert "Environment" in result or "WEAK" in result


class TestAuditRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "audit" in reg.categories
        expected = ["security", "secrets", "tls", "dependencies",
                    "permissions", "docker", "hashchain", "compliance", "env"]
        for cmd in expected:
            assert cmd in reg._commands["audit"]
