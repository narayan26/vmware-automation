#!/usr/bin/env python3
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from decouple import config
import ssl
import atexit

def connect_to_vcenter():
    """Connect to vCenter server and return the service instance."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.verify_mode = ssl.CERT_NONE  # Disable SSL verification (use proper certificates in production)
    
    si = SmartConnect(
        host=config('VCENTER_HOST'),
        user=config('VCENTER_USER'),
        pwd=config('VCENTER_PASSWORD'),
        port=int(config('VCENTER_PORT')),
        sslContext=context
    )
    atexit.register(Disconnect, si)
    return si

def create_vm(si, vm_name, datacenter_name, host_name, datastore_name, memory_mb=1024, num_cpus=1):
    """Create a virtual machine with the specified configuration."""
    content = si.RetrieveContent()
    
    # Get datacenter
    datacenter = None
    for dc in content.rootFolder.childEntity:
        if dc.name == datacenter_name:
            datacenter = dc
            break
    if not datacenter:
        raise Exception(f"Datacenter {datacenter_name} not found")

    # Get host
    host = None
    for cluster in datacenter.hostFolder.childEntity:
        for host_system in cluster.host:
            if host_system.name == host_name:
                host = host_system
                break
        if host:
            break
    if not host:
        raise Exception(f"Host {host_name} not found")

    # Get datastore
    datastore = None
    for ds in host.datastore:
        if ds.name == datastore_name:
            datastore = ds
            break
    if not datastore:
        raise Exception(f"Datastore {datastore_name} not found")

    # VM Configuration
    vmx_file = vim.vm.FileInfo(logDirectory=None,
                              snapshotDirectory=None,
                              suspendDirectory=None,
                              vmPathName=f"[{datastore_name}] {vm_name}/{vm_name}.vmx")
    
    config = vim.vm.ConfigSpec(
        name=vm_name,
        memoryMB=memory_mb,
        numCPUs=num_cpus,
        files=vmx_file,
        guestId='otherGuest64',  # Modify this based on your OS requirements
        version='vmx-19'  # Compatible with vSphere 8.0
    )

    # Create VM
    vm_folder = datacenter.vmFolder
    task = vm_folder.CreateVM_Task(config=config, pool=host.parent.resourcePool)
    print(f"Creating VM {vm_name}...")
    return task

def main():
    try:
        # Connect to vCenter
        si = connect_to_vcenter()
        print("Successfully connected to vCenter")

        # Example VM creation (modify these parameters as needed)
        vm_name = "TestVM"
        datacenter_name = "Your-Datacenter"
        host_name = "your-esxi-host.domain.com"
        datastore_name = "your-datastore"

        task = create_vm(
            si=si,
            vm_name=vm_name,
            datacenter_name=datacenter_name,
            host_name=host_name,
            datastore_name=datastore_name,
            memory_mb=2048,
            num_cpus=2
        )

        # Wait for the task to complete
        task_info = task.info
        while task_info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            task_info = task.info
        
        if task_info.state == vim.TaskInfo.State.success:
            print(f"VM {vm_name} created successfully!")
        else:
            print(f"Failed to create VM: {task_info.error.msg}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
