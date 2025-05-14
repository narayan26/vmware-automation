# VMware vCenter VM Creation Script

This Python script allows you to connect to a VMware vCenter server and create virtual machines programmatically.

## Prerequisites

- Python 3.x
- Access to a VMware vCenter server
- Required Python packages (installed via requirements.txt)

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and update with your vCenter credentials:
   ```
   cp .env.example .env
   ```
4. Edit the `.env` file with your vCenter server details

## Usage

Modify the parameters in the `main()` function of `create_vm.py` to match your environment:
- vm_name: Name of the new VM
- datacenter_name: Name of your vCenter datacenter
- host_name: Name of the ESXi host
- datastore_name: Name of the datastore where the VM will be created

Then run the script:
```
python create_vm.py
```

## Security Note

The script uses SSL verification disable for development purposes. In a production environment, you should use proper SSL certificates and enable verification.
