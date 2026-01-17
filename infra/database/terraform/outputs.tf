output "vm_details" {
  description = "VM names and their public IP addresses"
  value = {
    for i in range(1) : azurerm_linux_virtual_machine.vm[i].name => azurerm_public_ip.publicip[i].ip_address
  }
}