# Cosmos DB NoSQL account (cosmos-agentic-joel-dev).
# Stores chat history data in workshop mode (USE_CHAT_HISTORY_ENABLED=true).
# Uses serverless capacity (EnableServerless capability); no provisioned throughput.
# Child resources (database and container) are declared below.
resource "azurerm_cosmosdb_account" "res-10" {
  automatic_failover_enabled   = true
  create_mode                  = "Default"
  ip_range_filter              = ["13.88.56.148", "13.91.105.215", "181.122.62.132", "181.122.62.61", "4.210.172.107", "40.91.218.243"]
  local_authentication_enabled = true
  location                     = "eastus"
  name                         = "cosmos-agentic-joel-dev"
  offer_type                   = "Standard"
  resource_group_name          = azurerm_resource_group.res-0.name
  tags = {
    defaultExperience       = "Core (SQL)"
    hidden-cosmos-mmspecial = ""
    hidden-workload-type    = "Development/Testing"
  }
  analytical_storage {
    schema_type = "WellDefined"
  }
  backup {
    tier = "Continuous7Days"
    type = "Continuous"
  }
  capabilities {
    name = "EnableServerless"
  }
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    failover_priority = 0
    location          = "eastus"
  }
}

# The SQL API database within the Cosmos DB account.
# Named "chat-history" in the live environment (confirmed via Azure CLI).
# Note: the Bicep template uses "db_conversation_history" — this config reflects
# the actual deployed name.
resource "azurerm_cosmosdb_sql_database" "res-11" {
  account_name        = "cosmos-agentic-joel-dev"
  name                = "chat-history"
  resource_group_name = azurerm_resource_group.res-0.name
  depends_on = [
    azurerm_cosmosdb_account.res-10,
  ]
}

# The conversations container — partition key /userId (Hash, version 2).
# No throughput argument: serverless accounts do not use provisioned throughput.
# This container stores individual conversation records for the chat history feature.
resource "azurerm_cosmosdb_sql_container" "res-12" {
  account_name          = "cosmos-agentic-joel-dev"
  database_name         = "chat-history"
  name                  = "conversations"
  partition_key_paths   = ["/userId"]
  partition_key_version = 2
  resource_group_name   = azurerm_resource_group.res-0.name
  conflict_resolution_policy {
    conflict_resolution_path = "/_ts"
    mode                     = "LastWriterWins"
  }
  indexing_policy {
    included_path {
      path = "/*"
    }
  }
  depends_on = [
    azurerm_cosmosdb_sql_database.res-11,
  ]
}

# Cosmos DB SQL role assignment — grants Data Contributor access to the application
# managed identity (principal_id: 723f0a91-97f9-491f-85ba-e137eb06fab4).
resource "azurerm_cosmosdb_sql_role_assignment" "res-19" {
  account_name        = "cosmos-agentic-joel-dev"
  name                = "8a463205-a8cc-40cf-a481-e80ac4796f3b"
  principal_id        = "723f0a91-97f9-491f-85ba-e137eb06fab4"
  resource_group_name = azurerm_resource_group.res-0.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.res-21.id
  scope               = azurerm_cosmosdb_account.res-10.id
}

# Built-in Cosmos DB Data Reader role definition (read-only).
resource "azurerm_cosmosdb_sql_role_definition" "res-20" {
  account_name        = "cosmos-agentic-joel-dev"
  assignable_scopes   = [azurerm_cosmosdb_account.res-10.id]
  name                = "Cosmos DB Built-in Data Reader"
  resource_group_name = azurerm_resource_group.res-0.name
  role_definition_id  = "00000000-0000-0000-0000-000000000001"
  type                = "BuiltInRole"
  permissions {
    data_actions = ["Microsoft.DocumentDB/databaseAccounts/readMetadata", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/readChangeFeed"]
  }
}

# Built-in Cosmos DB Data Contributor role definition (read+write).
resource "azurerm_cosmosdb_sql_role_definition" "res-21" {
  account_name        = "cosmos-agentic-joel-dev"
  assignable_scopes   = [azurerm_cosmosdb_account.res-10.id]
  name                = "Cosmos DB Built-in Data Contributor"
  resource_group_name = azurerm_resource_group.res-0.name
  role_definition_id  = "00000000-0000-0000-0000-000000000002"
  type                = "BuiltInRole"
  permissions {
    data_actions = ["Microsoft.DocumentDB/databaseAccounts/readMetadata", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"]
  }
}
