# The organizational container for all application-owned Azure resources.
# All other resources in this configuration reside within this resource group.
resource "azurerm_resource_group" "res-0" {
  location = "eastus"
  name     = "AI-103-Study-Lab"
}
