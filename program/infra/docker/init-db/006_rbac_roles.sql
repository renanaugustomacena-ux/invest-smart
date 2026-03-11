-- ============================================================
-- MONEYMAKER V1 - RBAC Setup (Role-Based Access Control)
-- ============================================================
-- Creates per-service roles with minimal required privileges.
-- Principle of least privilege: each service can only access
-- the tables it needs for its specific function.
--
-- IMPORTANT: Passwords are set via 007_rbac_passwords.sh
-- using environment variables, NOT hardcoded here.
--
-- Roles created:
--   - data_ingestion_svc: Write market data (ohlcv_bars, market_ticks)
--   - algo_engine_svc: Read market/ML/macro data, write signals
--   - mt5_bridge_svc: Read signals, write executions
--   - moneymaker_admin: Full access for migrations/maintenance
-- ============================================================

-- ============================================================
-- 1. Create Roles
-- ============================================================

-- Data Ingestion Service: writes market data
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'data_ingestion_svc') THEN
        CREATE ROLE data_ingestion_svc WITH LOGIN;
        RAISE NOTICE 'Created role: data_ingestion_svc';
    END IF;
END $$;

-- Algo Engine Service: reads market data, writes signals
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'algo_engine_svc') THEN
        CREATE ROLE algo_engine_svc WITH LOGIN;
        RAISE NOTICE 'Created role: algo_engine_svc';
    END IF;
END $$;

-- MT5 Bridge Service: reads signals, writes executions
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mt5_bridge_svc') THEN
        CREATE ROLE mt5_bridge_svc WITH LOGIN;
        RAISE NOTICE 'Created role: mt5_bridge_svc';
    END IF;
END $$;

-- Admin role for migrations and maintenance
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'moneymaker_admin') THEN
        CREATE ROLE moneymaker_admin WITH LOGIN CREATEDB CREATEROLE;
        RAISE NOTICE 'Created role: moneymaker_admin';
    END IF;
END $$;

-- ============================================================
-- 2. Grant Schema and Database Access
-- ============================================================

GRANT CONNECT ON DATABASE moneymaker TO data_ingestion_svc, algo_engine_svc, mt5_bridge_svc, moneymaker_admin;
GRANT USAGE ON SCHEMA public TO data_ingestion_svc, algo_engine_svc, mt5_bridge_svc, moneymaker_admin;

-- ============================================================
-- 3. Data Ingestion Service Permissions
-- ============================================================
-- Function: Writes market data (ohlcv_bars, market_ticks)
-- Minimal read access for deduplication checks

-- Market data tables (primary writer)
GRANT INSERT, SELECT ON ohlcv_bars TO data_ingestion_svc;
GRANT INSERT, SELECT ON market_ticks TO data_ingestion_svc;

-- Macro data tables (primary writer for data fetchers)
GRANT INSERT, SELECT ON vix_data TO data_ingestion_svc;
GRANT INSERT, SELECT ON yield_curve_data TO data_ingestion_svc;
GRANT INSERT, SELECT ON real_rates_data TO data_ingestion_svc;
GRANT INSERT, SELECT ON dxy_data TO data_ingestion_svc;
GRANT INSERT, SELECT ON cot_reports TO data_ingestion_svc;
GRANT INSERT, SELECT ON recession_probability TO data_ingestion_svc;

-- Economic calendar (primary writer)
GRANT INSERT, SELECT ON economic_events TO data_ingestion_svc;
GRANT INSERT, SELECT ON trading_blackouts TO data_ingestion_svc;

-- Sequence access for SERIAL columns
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO data_ingestion_svc;

-- Audit log (append-only)
GRANT INSERT ON audit_log TO data_ingestion_svc;

-- ============================================================
-- 4. Algo Engine Service Permissions
-- ============================================================
-- Function: Reads market/ML/macro data, writes trading signals

-- Read market data
GRANT SELECT ON ohlcv_bars TO algo_engine_svc;
GRANT SELECT ON market_ticks TO algo_engine_svc;

-- Read macro data
GRANT SELECT ON vix_data TO algo_engine_svc;
GRANT SELECT ON yield_curve_data TO algo_engine_svc;
GRANT SELECT ON real_rates_data TO algo_engine_svc;
GRANT SELECT ON dxy_data TO algo_engine_svc;
GRANT SELECT ON cot_reports TO algo_engine_svc;
GRANT SELECT ON recession_probability TO algo_engine_svc;

-- Read economic calendar
GRANT SELECT ON economic_events TO algo_engine_svc;
GRANT SELECT ON trading_blackouts TO algo_engine_svc;
GRANT SELECT ON event_impact_rules TO algo_engine_svc;

-- Read strategy performance
GRANT SELECT ON strategy_performance TO algo_engine_svc;

-- Write trading signals (primary output)
GRANT INSERT, SELECT ON trading_signals TO algo_engine_svc;

-- Write strategy performance
GRANT INSERT, SELECT, UPDATE ON strategy_performance TO algo_engine_svc;

-- Sequence access
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO algo_engine_svc;

-- Audit log (append-only)
GRANT INSERT ON audit_log TO algo_engine_svc;

-- ============================================================
-- 5. MT5 Bridge Service Permissions
-- ============================================================
-- Function: Reads signals, writes trade executions

-- Read signals to execute
GRANT SELECT ON trading_signals TO mt5_bridge_svc;

-- Update signals (mark as executed)
GRANT UPDATE ON trading_signals TO mt5_bridge_svc;

-- Write trade executions (primary output)
GRANT INSERT, SELECT ON trade_executions TO mt5_bridge_svc;

-- Update strategy performance with execution results
GRANT UPDATE ON strategy_performance TO mt5_bridge_svc;

-- Sequence access
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mt5_bridge_svc;

-- Audit log (append-only)
GRANT INSERT ON audit_log TO mt5_bridge_svc;

-- ============================================================
-- 6. Admin Role Permissions
-- ============================================================
-- Full access for migrations and maintenance

GRANT ALL PRIVILEGES ON DATABASE moneymaker TO moneymaker_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO moneymaker_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO moneymaker_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO moneymaker_admin;

-- Admin can grant to others
ALTER ROLE moneymaker_admin WITH CREATEROLE;

-- ============================================================
-- 7. Add Service Identity to Audit Log
-- ============================================================
-- Track which service role wrote each audit entry

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_log' AND column_name = 'service_role'
    ) THEN
        ALTER TABLE audit_log ADD COLUMN service_role TEXT DEFAULT current_user;
        RAISE NOTICE 'Added service_role column to audit_log';
    END IF;
END $$;

-- ============================================================
-- 8. Default Privileges for Future Tables
-- ============================================================
-- Ensure new tables created by admin are accessible

ALTER DEFAULT PRIVILEGES FOR ROLE moneymaker IN SCHEMA public
    GRANT SELECT ON TABLES TO algo_engine_svc;

ALTER DEFAULT PRIVILEGES FOR ROLE moneymaker IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO data_ingestion_svc, algo_engine_svc, mt5_bridge_svc;

-- ============================================================
-- 9. Verification Query
-- ============================================================
-- Run this to check grants after setup:
/*
SELECT
    grantee,
    table_name,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE grantee IN ('data_ingestion_svc', 'algo_engine_svc', 'mt5_bridge_svc')
GROUP BY grantee, table_name
ORDER BY grantee, table_name;
*/

-- ============================================================
-- Success Message
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'RBAC setup complete!';
    RAISE NOTICE 'Roles created:';
    RAISE NOTICE '  - data_ingestion_svc (market data writer)';
    RAISE NOTICE '  - algo_engine_svc (signal generator)';
    RAISE NOTICE '  - mt5_bridge_svc (trade executor)';
    RAISE NOTICE '  - moneymaker_admin (full access)';
    RAISE NOTICE '';
    RAISE NOTICE 'NOTE: Passwords must be set via 007_rbac_passwords.sh';
    RAISE NOTICE '===========================================';
END $$;
