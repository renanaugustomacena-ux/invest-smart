"""Tests for database maintenance commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.maint import (
    _maint_backup,
    _maint_chunk_stats,
    _maint_clear_cache,
    _maint_compress,
    _maint_integrity,
    _maint_migrate,
    _maint_prune_old,
    _maint_reindex,
    _maint_restore,
    _maint_retention,
    _maint_sanitize,
    _maint_table_sizes,
    _maint_vacuum,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestMaintArgValidation:
    def test_restore_no_args(self):
        result = _maint_restore()
        assert "Usage" in result

    def test_restore_with_file(self):
        result = _maint_restore("backup.sql")
        assert "backup.sql" in result

    def test_prune_old_no_args(self):
        result = _maint_prune_old()
        assert "Usage" in result


class TestMaintRetention:
    def test_shows_retention_info(self):
        result = _maint_retention()
        assert "Retention" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestMaintWithClients:
    def test_vacuum(self, mock_cf):
        mock_db = MagicMock()
        mock_db.execute.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_vacuum()
        assert "[success]" in result

    def test_vacuum_error(self, mock_cf):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("db error")
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_vacuum()
        assert "[error]" in result

    def test_reindex(self, mock_cf):
        mock_db = MagicMock()
        mock_db.execute.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_reindex()
        assert "[success]" in result

    def test_table_sizes_found(self, mock_cf):
        mock_db = MagicMock()
        # Columns: tbl, total, data, idx
        mock_db.query.return_value = [
            ("public.ohlcv_bars", "200 MB", "150 MB", "50 MB"),
            ("public.market_ticks", "150 MB", "120 MB", "30 MB"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_table_sizes()
        assert "ohlcv_bars" in result

    def test_table_sizes_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_table_sizes()
        assert "No" in result

    def test_chunk_stats_found(self, mock_cf):
        mock_db = MagicMock()
        # Columns: hypertable_name, num_chunks, oldest, newest
        mock_db.query.return_value = [
            ("ohlcv_bars", 100, "2024-01-01", "2024-06-01"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_chunk_stats()
        assert "ohlcv_bars" in result or "Chunk" in result

    def test_chunk_stats_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_chunk_stats()
        assert "No" in result

    def test_compress_found(self, mock_cf):
        mock_db = MagicMock()
        # First query returns hypertable list, then execute compresses
        mock_db.query.return_value = [("ohlcv_bars",)]
        mock_db.execute.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_compress()
        assert "compress" in result.lower() or "Compressing" in result

    def test_compress_no_hypertables(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_compress()
        assert "No" in result

    def test_integrity_ok(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.side_effect = [(100,), (0,)]
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_integrity()
        assert "Integrity" in result

    def test_prune_old_valid(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (50,)
        mock_db.execute.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_prune_old("90")
        assert "90" in result

    def test_prune_old_dry_run(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (50,)
        mock_cf.get_postgres.return_value = mock_db
        result = _maint_prune_old("90", "--dry-run")
        assert "dry-run" in result


class TestMaintClearCache:
    @patch("moneymaker_console.commands.maint.run_tool")
    def test_clear_basic(self, mock_run):
        mock_run.return_value = ""
        result = _maint_clear_cache()
        assert "[success]" in result

    @patch("moneymaker_console.clients.ClientFactory")
    @patch("moneymaker_console.commands.maint.run_tool")
    def test_clear_with_redis(self, mock_run, mock_cf):
        mock_run.return_value = ""
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _maint_clear_cache("--redis")
        assert "[success]" in result


class TestMaintSubprocessCmds:
    @patch("moneymaker_console.commands.maint.run_tool")
    def test_backup(self, mock_run):
        mock_run.return_value = "[success] backup complete"
        result = _maint_backup()
        assert "backup" in result.lower() or "Backup" in result

    @patch("moneymaker_console.commands.maint.run_tool_live")
    def test_migrate(self, mock_run):
        mock_run.return_value = "[success] migration complete"
        result = _maint_migrate()
        assert mock_run.called

    @patch("moneymaker_console.commands.maint.run_tool_live")
    def test_migrate_dry_run(self, mock_run):
        result = _maint_migrate("--dry-run")
        assert "dry-run" in result or "info" in result.lower()
        assert not mock_run.called

    @patch("moneymaker_console.commands.maint.run_tool")
    def test_sanitize(self, mock_run):
        mock_run.return_value = ""
        result = _maint_sanitize()
        assert "Sanitization" in result


class TestMaintRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "maint" in reg.categories
        expected = [
            "vacuum",
            "reindex",
            "clear-cache",
            "retention",
            "backup",
            "restore",
            "table-sizes",
            "chunk-stats",
            "compress",
            "integrity",
        ]
        for cmd in expected:
            assert cmd in reg._commands["maint"]
