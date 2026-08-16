 setting-- Service Principal: app-24agm8 mwua-data-mgmt
-- Application ID:    ec20b8a6-556d-4bc7-ba88-81030099a394

-- 1. Catalog-level access
GRANT USE CATALOG ON CATALOG mwua_capstone_team3 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;

-- 2. Silver schema: READ pipeline-produced tables
GRANT USE SCHEMA ON SCHEMA mwua_capstone_team3.silver 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;
GRANT SELECT ON SCHEMA mwua_capstone_team3.silver 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;

-- 3. Governance schema: READ + WRITE (app creates & manages these)
GRANT USE SCHEMA ON SCHEMA mwua_capstone_team3.governance 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;
GRANT CREATE TABLE ON SCHEMA mwua_capstone_team3.governance 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;
GRANT SELECT, MODIFY ON SCHEMA mwua_capstone_team3.governance 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;

-- 4. SQL Warehouse access
GRANT CAN USE ON SQL WAREHOUSE `Serverless Starter Warehouse` 
  TO `ec20b8a6-556d-4bc7-ba88-81030099a394`;
