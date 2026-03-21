"""Tests for MacroDataScheduler.

No unittest.mock — uses real async callables with call tracking.
"""

from __future__ import annotations

import asyncio

from external_data.scheduler import MacroDataScheduler


# ---------------------------------------------------------------------------
# Test doubles (NOT mocks — real implementations with tracking)
# ---------------------------------------------------------------------------


class AsyncCallTracker:
    """Real async callable that tracks invocations."""

    def __init__(self, side_effect: Exception | None = None):
        self.call_count = 0
        self.called = False
        self._side_effect = side_effect

    async def __call__(self):
        self.call_count += 1
        self.called = True
        if self._side_effect:
            raise self._side_effect


class CancellableTask:
    """Test double for asyncio.Task — tracks cancel() calls."""

    def __init__(self):
        self.cancel_count = 0

    def cancel(self):
        self.cancel_count += 1


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMacroDataScheduler:
    def test_init(self):
        scheduler = MacroDataScheduler()
        assert scheduler._jobs == {}
        assert scheduler._running is False
        assert scheduler._tasks == {}
        assert scheduler.is_running is False

    def test_add_job(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker()

        scheduler.add_job("test_job", func, interval_seconds=60, run_immediately=True)

        assert "test_job" in scheduler._jobs
        job = scheduler._jobs["test_job"]
        assert job["func"] is func
        assert job["interval"] == 60
        assert job["run_immediately"] is True
        assert job["last_run"] is None
        assert job["run_count"] == 0
        assert job["error_count"] == 0

    def test_add_job_no_immediate(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker()

        scheduler.add_job("test_job", func, interval_seconds=30, run_immediately=False)

        assert scheduler._jobs["test_job"]["run_immediately"] is False

    def test_remove_job_exists(self):
        scheduler = MacroDataScheduler()
        scheduler.add_job("test_job", AsyncCallTracker(), interval_seconds=60)

        result = scheduler.remove_job("test_job")
        assert result is True
        assert "test_job" not in scheduler._jobs

    def test_remove_job_not_found(self):
        scheduler = MacroDataScheduler()
        result = scheduler.remove_job("nonexistent")
        assert result is False

    def test_remove_job_cancels_task(self):
        scheduler = MacroDataScheduler()
        scheduler.add_job("test_job", AsyncCallTracker(), interval_seconds=60)

        # Simulate a running task with a real test double
        fake_task = CancellableTask()
        scheduler._tasks["test_job"] = fake_task

        result = scheduler.remove_job("test_job")
        assert result is True
        assert fake_task.cancel_count == 1

    async def test_execute_job_success(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker()
        scheduler.add_job("test_job", func, interval_seconds=60)

        await scheduler._execute_job("test_job", func)

        assert func.call_count == 1
        assert scheduler._jobs["test_job"]["run_count"] == 1
        assert scheduler._jobs["test_job"]["last_run"] is not None

    async def test_execute_job_error(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker(side_effect=ValueError("test error"))
        scheduler.add_job("test_job", func, interval_seconds=60)

        await scheduler._execute_job("test_job", func)

        assert scheduler._jobs["test_job"]["error_count"] == 1
        assert scheduler._jobs["test_job"]["run_count"] == 0

    async def test_execute_job_missing(self):
        scheduler = MacroDataScheduler()
        # Should not raise for missing job
        await scheduler._execute_job("nonexistent", AsyncCallTracker())

    async def test_start_and_stop(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker()
        scheduler.add_job("test_job", func, interval_seconds=3600, run_immediately=False)

        await scheduler.start()
        assert scheduler.is_running is True
        assert "test_job" in scheduler._tasks

        await scheduler.stop()
        assert scheduler.is_running is False
        assert len(scheduler._tasks) == 0

    async def test_start_idempotent(self):
        scheduler = MacroDataScheduler()
        scheduler.add_job("job", AsyncCallTracker(), interval_seconds=3600, run_immediately=False)

        await scheduler.start()
        # Second start should be a no-op
        await scheduler.start()

        assert scheduler.is_running is True
        await scheduler.stop()

    async def test_stop_when_not_running(self):
        scheduler = MacroDataScheduler()
        # Should not raise
        await scheduler.stop()
        assert scheduler.is_running is False

    async def test_start_runs_immediate_job(self):
        scheduler = MacroDataScheduler()
        func = AsyncCallTracker()
        scheduler.add_job("test_job", func, interval_seconds=3600, run_immediately=True)

        await scheduler.start()
        # Give time for immediate execution
        await asyncio.sleep(0.1)
        await scheduler.stop()

        assert func.called

    def test_get_job_stats_empty(self):
        scheduler = MacroDataScheduler()
        stats = scheduler.get_job_stats()
        assert stats == {}

    def test_get_job_stats(self):
        scheduler = MacroDataScheduler()
        scheduler.add_job("job1", AsyncCallTracker(), interval_seconds=60)
        scheduler.add_job("job2", AsyncCallTracker(), interval_seconds=120)

        stats = scheduler.get_job_stats()

        assert "job1" in stats
        assert "job2" in stats
        assert stats["job1"]["interval_seconds"] == 60
        assert stats["job1"]["run_count"] == 0
        assert stats["job1"]["error_count"] == 0
        assert stats["job1"]["last_run"] is None
        assert stats["job2"]["interval_seconds"] == 120

    def test_is_running_property(self):
        scheduler = MacroDataScheduler()
        assert scheduler.is_running is False
        scheduler._running = True
        assert scheduler.is_running is True
