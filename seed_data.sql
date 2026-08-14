-- Seed data for MWUA governance tables
-- Run this after creating the governance schema and tables

-- Create governance schema if not exists
CREATE SCHEMA IF NOT EXISTS mwua_capstone_team3.governance;

-- Zone Master (matches sensor data zones A-F)
CREATE TABLE IF NOT EXISTS mwua_capstone_team3.governance.zone_master (
  zone_id STRING, zone_name STRING, zone_description STRING,
  region STRING, is_active BOOLEAN, created_by STRING,
  created_at TIMESTAMP, updated_at TIMESTAMP
);

DELETE FROM mwua_capstone_team3.governance.zone_master;
INSERT INTO mwua_capstone_team3.governance.zone_master VALUES
  ('ZONE_A', 'Zone A - Bukit Timah', 'Water network zone covering Bukit Timah area', 'Central', true, 'admin', current_timestamp(), current_timestamp()),
  ('ZONE_B', 'Zone B - Tampines', 'Water network zone covering Tampines area', 'East', true, 'admin', current_timestamp(), current_timestamp()),
  ('ZONE_C', 'Zone C - Jurong', 'Water network zone covering Jurong area', 'West', true, 'admin', current_timestamp(), current_timestamp()),
  ('ZONE_D', 'Zone D - Woodlands', 'Water network zone covering Woodlands area', 'North', true, 'admin', current_timestamp(), current_timestamp()),
  ('ZONE_E', 'Zone E - Punggol', 'Water network zone covering Punggol area', 'Northeast', true, 'admin', current_timestamp(), current_timestamp()),
  ('ZONE_F', 'Zone F - Pasir Ris', 'Water network zone covering Pasir Ris area', 'East', true, 'admin', current_timestamp(), current_timestamp());

-- Business Rules
CREATE TABLE IF NOT EXISTS mwua_capstone_team3.governance.config_business_rules (
  rule_id STRING, rule_name STRING, rule_category STRING,
  parameter_name STRING, parameter_value STRING, data_type STRING,
  description STRING, is_active BOOLEAN, updated_by STRING, updated_at TIMESTAMP
);

DELETE FROM mwua_capstone_team3.governance.config_business_rules;
INSERT INTO mwua_capstone_team3.governance.config_business_rules VALUES
  ('R001', 'Max Flow Rate', 'sensor_threshold', 'max_flow_rate', '150.0', 'float', 'Maximum acceptable flow rate (L/min)', true, 'admin', current_timestamp()),
  ('R002', 'Min Pressure', 'sensor_threshold', 'min_pressure', '0.5', 'float', 'Minimum acceptable pressure (bar)', true, 'admin', current_timestamp()),
  ('R003', 'Max Pressure', 'sensor_threshold', 'max_pressure', '10.0', 'float', 'Maximum acceptable pressure (bar)', true, 'admin', current_timestamp()),
  ('R004', 'Billing Tolerance', 'billing_validation', 'consumption_tolerance_pct', '20.0', 'float', 'Max % deviation from average consumption', true, 'admin', current_timestamp()),
  ('R005', 'Min Billing Amount', 'billing_validation', 'min_amount', '0.0', 'float', 'Minimum valid billing amount', true, 'admin', current_timestamp()),
  ('R006', 'Duplicate Window', 'dq_check', 'duplicate_window_hours', '24', 'int', 'Hours within which readings are checked for duplicates', true, 'admin', current_timestamp()),
  ('R007', 'Null Threshold', 'dq_check', 'max_null_pct', '5.0', 'float', 'Maximum % of null values allowed per batch', true, 'admin', current_timestamp());

-- Data Corrections (empty - populated by app)
CREATE TABLE IF NOT EXISTS mwua_capstone_team3.governance.data_corrections (
  correction_id STRING, source_table STRING, record_id STRING,
  field_name STRING, original_value STRING, corrected_value STRING,
  reason STRING, status STRING, submitted_by STRING,
  submitted_at TIMESTAMP, approved_by STRING, approved_at TIMESTAMP
);

-- Audit Changes (empty - populated by app)
CREATE TABLE IF NOT EXISTS mwua_capstone_team3.governance.audit_changes (
  audit_id STRING, table_name STRING, record_id STRING,
  action STRING, field_name STRING, old_value STRING,
  new_value STRING, reason STRING, changed_by STRING, changed_at TIMESTAMP
);
