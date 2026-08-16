# MWUA Data Management App

A Databricks App for managing MWUA (Metropolitan Water Utility Authority) data operations — covering data quality monitoring, zone governance, business rule configuration, and data correction workflows.

## Features

### 📊 Data Quality Overview
- Summary cards showing sensor DQ records, billing quarantined count, DQ pass rate, and pending corrections
- Active zone and rule counts at a glance
- **DQ Trend Charts**: Billing DQ trend (valid vs quarantined vs duplicates over time), sensor issues by reason (bar chart), and sensor DQ by zone (stacked bar)

### 🗺️ Zone Management
- View all zones with active/inactive status (inactive rows highlighted in red)
- **Add Zone**: Create new zones with validation (Zone ID must be alphanumeric with underscores/hyphens; Zone Name required)
- **Edit Zone**: Select from a dropdown of active zones and update the zone name
- **Deactivate Zone**: Select from a dropdown of active zones, provide a reason, and mark as inactive
- All changes auto-refresh the zone table immediately and are logged to the audit trail

### ⚙️ Business Rules & Thresholds
- View active rules grouped by category (sensor_threshold, billing_validation, dq_check)
- **Add Rule**: Create rules with validation (Rule ID alphanumeric, Rule Name and Category required)
- **Edit Rule**: Select from a dropdown of active rules, update the parameter value with a mandatory reason
- **Deactivate Rule**: Select from a dropdown of active rules with a mandatory reason
- All changes auto-refresh and are logged to the audit trail

### 🔍 Data Quality & Corrections
- **Sensor DQ Issues tab**: Browse flagged sensor readings with DQ reason and status
- **Billing Quarantine tab**: Browse quarantined billing records with rejection reasons
- **Submitted Corrections tab**: Track correction requests and their status (PENDING highlighted)
- **Submit Data Correction**: Select source table → record ID dropdown → field dropdown → provide corrected value and reason
  - Original values are auto-fetched for traceability
  - Corrections are applied downstream (not to Bronze layer)
  - Auto-refreshes the corrections tab after submission

### 📝 Audit History
- Full audit trail of all changes (add, update, deactivate, corrections)
- Shows who made the change, what changed (old → new values), and why
- Sortable columns, paginated display (latest 100 records)

## Input Validation

All forms enforce:
- Required fields with clear warning messages
- Alphanumeric ID format validation (underscores and hyphens allowed)
- Dropdown selection for edit/deactivate operations (prevents invalid ID entry)
- Mandatory reason fields for edits and deactivations

## Auto-Refresh Behaviour

- Zone and Rule tables automatically refresh after any add/edit/deactivate operation
- DQ Corrections tab auto-refreshes after submitting a new correction
- Manual "Refresh" button available on each page for on-demand data reload

## Architecture

The app connects to Unity Catalog tables via the Databricks SQL Connector:

**Reads from pipeline-produced tables (Silver):**
- `mwua_capstone_team3.silver.ops_silver_sensor_dq`
- `mwua_capstone_team3.silver.ops_quarantine_billing`
- `mwua_capstone_team3.silver.ops_silver_billing_dq_metrics`

**Writes to app-managed governance tables:**
- `mwua_capstone_team3.governance.zone_master`
- `mwua_capstone_team3.governance.config_business_rules`
- `mwua_capstone_team3.governance.data_corrections`
- `mwua_capstone_team3.governance.audit_changes`

## Connected Pipelines

- `uc1_billing_customer` — Billing and customer data pipeline
- `uc3_network_sensor` — Network sensor readings pipeline

## Setup

1. Deploy as a Databricks App
2. Run `grant_access.sql` statements to give the app's service principal access to the required tables
3. Set environment variables:
   - `CATALOG` — Unity Catalog name (default: `mwua_capstone_team3`)
   - `DATABRICKS_WAREHOUSE_PATH` — SQL warehouse HTTP path

## Tech Stack

- [Dash](https://dash.plotly.com/) with Bootstrap (Flatly theme)
- [Plotly](https://plotly.com/python/) for interactive charts
- Databricks SQL Connector for data access
- Databricks SDK for OAuth authentication
- `dcc.Store` for cross-component state management (auto-refresh triggers)
