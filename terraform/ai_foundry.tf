# Azure AI Foundry hub (ai-brain-openai).
# Exported as azurerm_cognitive_account (kind="AIServices") because the azurerm provider
# v4.80.0 maps Microsoft.CognitiveServices/accounts with AIServices kind to this resource
# type. The newer azurerm_ai_foundry type is not yet used by aztfexport v0.20.0.
# See known-gaps.md for details.
resource "azurerm_cognitive_account" "res-1" {
  custom_subdomain_name      = "ai-brain-openai"
  kind                       = "AIServices"
  location                   = "eastus"
  name                       = "ai-brain-openai"
  project_management_enabled = true
  resource_group_name        = azurerm_resource_group.res-0.name
  sku_name                   = "S0"
  identity {
    type = "SystemAssigned"
  }
  network_acls {
    default_action = "Allow"
  }
}

# GPT-4.1-mini model deployment on the AI hub.
# This deployment is a child resource of ai-brain-openai and is part of the
# application's AI inference infrastructure.
resource "azurerm_cognitive_deployment" "res-4" {
  cognitive_account_id = azurerm_cognitive_account.res-1.id
  name                 = "gpt-4.1-mini"
  rai_policy_name      = "Microsoft.DefaultV2"
  model {
    format  = "OpenAI"
    name    = "gpt-4.1-mini"
    version = "2025-04-14"
  }
  sku {
    capacity = 2500
    name     = "GlobalStandard"
  }
}

# Azure AI project (proj-default) — child of the AI hub (ai-brain-openai).
# Hosts the agent definitions and model deployments used by the application.
# Exported as azurerm_cognitive_account_project; parent dependency is expressed
# via cognitive_account_id referencing the hub above.
resource "azurerm_cognitive_account_project" "res-5" {
  cognitive_account_id = azurerm_cognitive_account.res-1.id
  description          = "Default project created with the resource"
  display_name         = "proj-default"
  location             = "eastus"
  name                 = "proj-default"
  identity {
    type = "SystemAssigned"
  }
}
