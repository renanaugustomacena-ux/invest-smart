"""Smoke tests for TUI and poller module imports."""


def test_tui_input_importable():
    from moneymaker_console.tui import input as tui_input

    assert hasattr(tui_input, "__name__")


def test_tui_renderer_importable():
    from moneymaker_console.tui import renderer

    assert hasattr(renderer, "__name__")


def test_market_poller_importable():
    from moneymaker_console.poller import market_poller

    assert hasattr(market_poller, "__name__")


def test_status_poller_importable():
    from moneymaker_console.poller import status_poller

    assert hasattr(status_poller, "__name__")
