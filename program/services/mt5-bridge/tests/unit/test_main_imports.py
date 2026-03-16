"""Smoke tests for MT5 Bridge module imports."""

from __future__ import annotations


def test_config_importable():
    from mt5_bridge import config

    assert hasattr(config, "MT5BridgeSettings")


def test_connector_importable():
    from mt5_bridge import connector

    assert hasattr(connector, "MT5Connector")


def test_grpc_server_importable():
    from mt5_bridge import grpc_server

    assert hasattr(grpc_server, "ExecutionServer")


def test_order_manager_importable():
    from mt5_bridge import order_manager

    assert hasattr(order_manager, "OrderManager")


def test_position_tracker_importable():
    from mt5_bridge import position_tracker

    assert hasattr(position_tracker, "PositionTracker")


def test_trade_recorder_importable():
    from mt5_bridge import trade_recorder

    assert hasattr(trade_recorder, "TradeRecorder")


def test_main_importable():
    from mt5_bridge import main

    assert hasattr(main, "main")
