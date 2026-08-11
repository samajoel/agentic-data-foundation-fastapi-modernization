output "resource_group_id" {
  description = "ARM resource ID of the application resource group."
  value       = azurerm_resource_group.res-0.id
}

output "cosmos_account_endpoint" {
  description = "Cosmos DB account endpoint URL."
  value       = azurerm_cosmosdb_account.res-10.endpoint
}

output "sql_server_fqdn" {
  description = "Fully qualified domain name of the Azure SQL server."
  value       = azurerm_mssql_server.res-25.fully_qualified_domain_name
}

output "ai_hub_id" {
  description = "ARM resource ID of the Azure AI Foundry hub (ai-brain-openai)."
  value       = azurerm_cognitive_account.res-1.id
}

output "ai_project_id" {
  description = "ARM resource ID of the Azure AI project (proj-default)."
  value       = azurerm_cognitive_account_project.res-5.id
}
