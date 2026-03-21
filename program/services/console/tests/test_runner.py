"""Tests for runner module — subprocess execution and output trimming.

No unittest.mock — uses real subprocess calls with simple, safe commands.
"""

from __future__ import annotations

from moneymaker_console.runner import (
    OUTPUT_TRIM_LINES,
    _build_env,
    run_tool,
    run_tool_live,
)


# ---------------------------------------------------------------------------
# _build_env
# ---------------------------------------------------------------------------


class TestBuildEnv:
    def test_includes_pythonpath(self):
        env = _build_env()
        assert "PYTHONPATH" in env

    def test_extra_vars_added(self):
        env = _build_env(extra={"MY_VAR": "hello"})
        assert env["MY_VAR"] == "hello"

    def test_extra_none_works(self):
        env = _build_env(extra=None)
        assert isinstance(env, dict)

    def test_inherits_system_env(self):
        import os
        env = _build_env()
        # Should have PATH from system
        assert "PATH" in env


# ---------------------------------------------------------------------------
# run_tool
# ---------------------------------------------------------------------------


class TestRunTool:
    def test_success_command(self):
        result = run_tool(["echo", "hello world"])
        assert "[success]" in result
        assert "hello world" in result

    def test_failing_command(self):
        result = run_tool(["false"])
        assert "[error]" in result

    def test_command_not_found(self):
        result = run_tool(["nonexistent_command_xyz_123"])
        assert "[error]" in result
        assert "not found" in result.lower() or "Command not found" in result

    def test_timeout(self):
        result = run_tool(["sleep", "10"], timeout=1)
        assert "[error]" in result
        assert "Timeout" in result

    def test_output_trimming(self):
        """Output longer than OUTPUT_TRIM_LINES gets trimmed."""
        # Generate 200 lines of output
        cmd = ["python3", "-c", f"for i in range({OUTPUT_TRIM_LINES + 50}): print(f'line {{i}}')"]
        result = run_tool(cmd)
        assert "omitted" in result

    def test_empty_output(self):
        result = run_tool(["true"])
        assert "[success]" in result

    def test_env_extra_passed(self):
        result = run_tool(
            ["python3", "-c", "import os; print(os.environ.get('TEST_VAR', 'missing'))"],
            env_extra={"TEST_VAR": "found"},
        )
        assert "found" in result


# ---------------------------------------------------------------------------
# run_tool_live
# ---------------------------------------------------------------------------


class TestRunToolLive:
    def test_success_command(self):
        result = run_tool_live(["echo", "hello"])
        assert "[success]" in result
        assert "exit code: 0" in result

    def test_failing_command(self):
        result = run_tool_live(["false"])
        assert "[error]" in result

    def test_command_not_found(self):
        result = run_tool_live(["nonexistent_cmd_abc_456"])
        assert "[error]" in result
        assert "Command not found" in result
