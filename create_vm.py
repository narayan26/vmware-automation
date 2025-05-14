#!/usr/bin/env python3
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from decouple import config
import ssl
import atexit
from concurrent.futures import ThreadPoolExecutor
import time

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

def create_vm(si, vm_name, datacenter_name, host_name, datastore_name, memory_mb=2048, num_cpus=2, guest_id='otherGuest64'):
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
        guestId=guest_id,
        version='vmx-19'  # Compatible with vSphere 8.0
    )

    # Create VM
    vm_folder = datacenter.vmFolder
    task = vm_folder.CreateVM_Task(config=config, pool=host.parent.resourcePool)
    print(f"Creating VM {vm_name}...")
    return task

def wait_for_task(task, vm_name):
    """Wait for a vSphere task to complete and return the result."""
    task_info = task.info
    while task_info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(2)  # Prevent excessive polling
        task_info = task.info
    
    if task_info.state == vim.TaskInfo.State.success:
        print(f"VM {vm_name} created successfully!")
        return True
    else:
        print(f"Failed to create VM {vm_name}: {task_info.error.msg}")
        return False

def create_single_vm(si, base_name, index, params):
    """Create a single VM with the given parameters."""
    vm_name = f"{base_name}-{index+1:03d}"
    try:
        task = create_vm(
            si=si,
            vm_name=vm_name,
            datacenter_name=params['datacenter_name'],
            host_name=params['host_name'],
            datastore_name=params['datastore_name'],
            memory_mb=params['memory_mb'],
            num_cpus=params['num_cpus'],
            guest_id=params['guest_id']
        )
        return wait_for_task(task, vm_name)
    except Exception as e:
        print(f"Error creating VM {vm_name}: {str(e)}")
        return False

def main():
    try:
        # Connect to vCenter
        si = connect_to_vcenter()
        print("Successfully connected to vCenter")

        # Get VM creation parameters from environment
        vm_params = {
            'base_name': config('VM_BASE_NAME'),
            'count': int(config('VM_COUNT', default='5')),
            'datacenter_name': config('VM_DATACENTER'),
            'host_name': config('VM_HOST'),
            'datastore_name': config('VM_DATASTORE'),
            'memory_mb': int(config('VM_MEMORY_MB', default='2048')),
            'num_cpus': int(config('VM_CPU_COUNT', default='2')),
            'guest_id': config('VM_GUEST_OS', default='otherGuest64')
        }

        # Validate VM count
        if not 1 <= vm_params['count'] <= 50:
            raise ValueError("VM_COUNT must be between 1 and 50")

        print(f"Starting creation of {vm_params['count']} VMs...")
        
        # Create VMs in parallel using a thread pool
        successful_vms = 0
        with ThreadPoolExecutor(max_workers=min(vm_params['count'], 10)) as executor:
            futures = []
            for i in range(vm_params['count']):
                future = executor.submit(
                    create_single_vm,
                    si,
                    vm_params['base_name'],
                    i,
                    {
                        'datacenter_name': vm_params['datacenter_name'],
                        'host_name': vm_params['host_name'],
                        'datastore_name': vm_params['datastore_name'],
                        'memory_mb': vm_params['memory_mb'],
                        'num_cpus': vm_params['num_cpus'],
                        'guest_id': vm_params['guest_id']
                    }
                )
                futures.append(future)
            
            # Wait for all VMs to be created
            for future in futures:
                if future.result():
                    successful_vms += 1

        print(f"\nVM Creation Summary:")
        print(f"Total VMs attempted: {vm_params['count']}")
        print(f"Successfully created: {successful_vms}")
        print(f"Failed: {vm_params['count'] - successful_vms}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
