provider "azurerm" {
  features {}
  subscription_id = "f36fcc7d-331c-434a-b6f3-97cc4a782cce"
}
terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
    random = {
      source = "hashicorp/random"
    }
    azapi = {
      source = "azure/azapi"
    }
  }
}
