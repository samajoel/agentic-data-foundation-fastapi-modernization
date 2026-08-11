# Azure SQL Server (sql-agentic-joel-dev).
# Located in westus2 — the only application resource not in eastus.
# Azure AD-only authentication is enabled (azuread_authentication_only = true);
# SQL administrator password-based login is disabled. No password appears in this config.
resource "azurerm_mssql_server" "res-25" {
  administrator_login = "CloudSA1c02efbc"
  location            = "westus2"
  name                = "sql-agentic-joel-dev"
  resource_group_name = azurerm_resource_group.res-0.name
  version             = "12.0"
  azuread_administrator {
    azuread_authentication_only = true
    login_username              = "mateo_god@hotmail.com"
    object_id                   = "723f0a91-97f9-491f-85ba-e137eb06fab4"
    tenant_id                   = "85d4980d-7d57-4a46-b9fc-0e4e3bc6603a"
  }
}

# The application SQL database (agentic-data-db).
# Used for structured data access in non-workshop mode (Fabric SQL / historyfab).
# SKU: GP_S_Gen5_1 (General Purpose Serverless, 1 vCore); auto-pause at 60 minutes.
resource "azurerm_mssql_database" "res-37" {
  auto_pause_delay_in_minutes    = 60
  collation                      = "SQL_Latin1_General_CP1_CI_AS"
  maintenance_configuration_name = "SQL_Default"
  max_size_gb                    = 32
  min_capacity                   = 0.5
  name                           = "agentic-data-db"
  server_id                      = azurerm_mssql_server.res-25.id
  sku_name                       = "GP_S_Gen5_1"
  storage_account_type           = "Local"
  long_term_retention_policy {
    monthly_retention = "PT0S"
    week_of_year      = 1
    weekly_retention  = "PT0S"
    yearly_retention  = "PT0S"
  }
  short_term_retention_policy {
    backup_interval_in_hours = 12
    retention_days           = 7
  }
  threat_detection_policy {
  }
}

# Extended auditing policy for the SQL database (currently disabled).
resource "azurerm_mssql_database_extended_auditing_policy" "res-43" {
  database_id            = azurerm_mssql_database.res-37.id
  enabled                = false
  log_monitoring_enabled = false
}

# Microsoft support auditing policy for the SQL server (currently disabled).
resource "azurerm_mssql_server_microsoft_support_auditing_policy" "res-58" {
  enabled                = false
  log_monitoring_enabled = false
  server_id              = azurerm_mssql_server.res-25.id
}

# Transparent data encryption for the SQL server (service-managed key).
resource "azurerm_mssql_server_transparent_data_encryption" "res-59" {
  server_id = azurerm_mssql_server.res-25.id
}

# Extended auditing policy for the SQL server (currently disabled).
resource "azurerm_mssql_server_extended_auditing_policy" "res-60" {
  enabled                = false
  log_monitoring_enabled = false
  server_id              = azurerm_mssql_server.res-25.id
}

# Firewall rule: allows access from the client IP recorded on 2026-08-07.
resource "azurerm_mssql_firewall_rule" "res-61" {
  end_ip_address   = "181.122.62.61"
  name             = "ClientIPAddress_2026-8-7_19-42-58"
  server_id        = azurerm_mssql_server.res-25.id
  start_ip_address = "181.122.62.61"
}

# Firewall rule: allows access from the client IP recorded on 2026-07-25.
resource "azurerm_mssql_firewall_rule" "res-62" {
  end_ip_address   = "181.91.84.33"
  name             = "ClientIp-2026-7-25_18-3-18"
  server_id        = azurerm_mssql_server.res-25.id
  start_ip_address = "181.91.84.33"
}

# Security alert policy for the SQL server (currently disabled).
resource "azurerm_mssql_server_security_alert_policy" "res-64" {
  resource_group_name = azurerm_resource_group.res-0.name
  server_name         = "sql-agentic-joel-dev"
  state               = "Disabled"
  depends_on = [
    azurerm_mssql_server.res-25,
  ]
}
