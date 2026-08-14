# MWUA Data Management App

A Databricks App for managing MWUA (Metropolitan Water Utility Authority) data operations.

## Features

- **Data Quality Overview** - Monitor DQ metrics from billing and sensor pipelines
- **Zone Management** - View, add, edit, deactivate zone master data
- **Business Rules** - Configure sensor thresholds and validation rules
- **Data Corrections** - Review flagged records and submit corrections (applied downstream, not to Bronze)
- **Audit History** - Track all changes with who/what/when/why

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

- `uc1_billing_customer` - Billing and customer data pipeline
- `uc3_network_sensor` - Network sensor readings pipeline

## Setup

1. Deploy as a Databricks App
2. Run `grant_access.sql` statements to give the app's service principal access
3. Create governance tables (app creates them on first use if they don't exist)

## Tech Stack

- [Dash](https://dash.plotly.com/) with Bootstrap (Flatly theme)
- Databricks SQL Connector
- Databricks SDK for authentication
