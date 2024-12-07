# ClickOps-Or-Terraform

A Python tool that identifies Azure resources created through the Azure Portal (ClickOps) by analyzing resource metadata and creation patterns. This tool helps organizations maintain infrastructure-as-code best practices by detecting resources that were manually created rather than through automation.

## Features

- Detects portal-created resources through metadata analysis
- Provides clear, formatted output for easy reading
- Supports single or multiple subscription analysis
- Identifies resources based on multiple detection methods:
  - Resource identity patterns
  - Tag analysis
  - Creation metadata inspection
- Exports results to CSV for further analysis

## Prerequisites

- Python 3.6+
- Azure CLI installed and configured
- Active Azure subscription(s)

## Installation

1. Install Azure CLI:
   - Windows: [Windows Installation Guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)
   - macOS: `brew install azure-cli`
   - Linux: [Linux Installation Guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux)

2. Clone the repository:
```bash
git clone https://github.com/ecrotty/ClickOps-Or-Terraform.git
cd ClickOps-Or-Terraform
```

3. No additional Python packages are required as this tool uses only standard library modules.

## Usage

Run the script with default options (interactive subscription selection):
```bash
python ClickOps-Or-Terraform.py
```

Export results to CSV:
```bash
python ClickOps-Or-Terraform.py --output results.csv
```

## How It Works

The tool uses several detection methods to identify resources likely created through the Azure Portal:

1. **Metadata Analysis**: Examines resource identity, managedBy, and createdBy fields for portal indicators
2. **Tag Analysis**: Checks for absence of automation-related tags (terraform, arm-template, etc.)
3. **Provisioning State**: Analyzes the resource's provisioning history

## Output Example

```
📦 Resource: example-vm
  Type: Microsoft.Compute/virtualMachines
  Resource Group: example-rg
  Tags:
    environment = development
  Created Time: 2023-08-15T10:30:00Z
  Portal Creation Indicators:
    • Resource has no automation-related tags
    • Resource was provisioned without automation tags
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the BSD-3-Clause License - see the [LICENSE](LICENSE) file for details.

## Author

Ed Crotty (ecrotty@edcrotty.com)

## Acknowledgments

- Azure CLI documentation and community
- Infrastructure as Code best practices
