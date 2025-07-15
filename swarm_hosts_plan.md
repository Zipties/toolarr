# Docker Swarm Hosts Configuration Plan

## Current Node Information
Based on previous data:
- dock-servarr: 192.168.45.15 (current node)
- docker-homestead: 192.168.45.11
- docker-lappy: 192.168.45.12
- docker-swarm (keepalived VIP): 192.168.45.10

## Objective
Configure /etc/hosts on all nodes so they can reach each other by hostname

## Plan

### Step 1: Create the hosts entries template
Create a standard hosts block that will be added to all nodes:
```
# Docker Swarm Cluster
192.168.45.10   docker-swarm
192.168.45.11   docker-homestead
192.168.45.12   docker-lappy
192.168.45.15   dock-servarr
```

### Step 2: Backup existing hosts files
On each node, backup the current hosts file:
```bash
cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d)
```

### Step 3: Check existing entries
For each node, check if any of these entries already exist to avoid duplicates

### Step 4: Add entries to each node
For each node, add the entries that don't already exist

### Step 5: Verify connectivity
Test hostname resolution from each node to all others

## Implementation Script
```bash
#!/bin/bash

# Define nodes
declare -A NODES=(
    ["dock-servarr"]="192.168.45.15"
    ["docker-homestead"]="192.168.45.11"
    ["docker-lappy"]="192.168.45.12"
)

# Hosts entries to add
HOSTS_BLOCK="
# Docker Swarm Cluster
192.168.45.10   docker-swarm
192.168.45.11   docker-homestead
192.168.45.12   docker-lappy
192.168.45.15   dock-servarr"

# Function to update hosts file
update_hosts() {
    local node=$1
    local ip=$2
    
    echo "Updating hosts on $node ($ip)..."
    
    # For current node
    if [[ "$node" == "dock-servarr" ]]; then
        # Local operations
        sudo cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d)
        
        # Check if entries exist
        if ! grep -q "Docker Swarm Cluster" /etc/hosts; then
            echo "$HOSTS_BLOCK" | sudo tee -a /etc/hosts
        else
            echo "Swarm hosts already configured on $node"
        fi
    else
        # Remote operations
        ssh root@$ip "cp /etc/hosts /etc/hosts.backup.\$(date +%Y%m%d)"
        
        # Check and add entries
        ssh root@$ip "grep -q 'Docker Swarm Cluster' /etc/hosts || echo '$HOSTS_BLOCK' >> /etc/hosts"
    fi
}

# Update all nodes
for node in "${!NODES[@]}"; do
    update_hosts "$node" "${NODES[$node]}"
done

# Verify connectivity
echo -e "\nVerifying hostname resolution..."
for source in "${!NODES[@]}"; do
    echo "From $source:"
    for target in "${!NODES[@]}"; do
        if [[ "$source" != "$target" ]]; then
            if [[ "$source" == "dock-servarr" ]]; then
                ping -c 1 -W 1 $target > /dev/null 2>&1 && echo "  ✓ $target" || echo "  ✗ $target"
            else
                ssh -o ConnectTimeout=2 root@${NODES[$source]} "ping -c 1 -W 1 $target > /dev/null 2>&1" && echo "  ✓ $target" || echo "  ✗ $target"
            fi
        fi
    done
done
```

## Safety Considerations
1. Always backup /etc/hosts before modification
2. Check for existing entries to avoid duplicates
3. Test one node first before applying to all
4. Have a rollback plan (restore from backup)

## Testing Process
1. Ping test: `ping -c 1 docker-homestead`
2. SSH test: `ssh root@docker-lappy hostname`
3. Docker test: `docker node ls` should show hostnames
4. Swarm VIP test: `ping -c 1 docker-swarm`
