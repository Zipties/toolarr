#!/bin/bash

# Define nodes with their IPs
declare -A NODES=(
    ["dock-servarr"]="192.168.45.15"
    ["docker-homestead"]="192.168.45.11"
    ["docker-lappy"]="192.168.45.12"
)

# Hosts entries to add
HOSTS_BLOCK="
# Docker Swarm Cluster (192.168.45.0/24 network)
192.168.45.10   docker-swarm
192.168.45.11   docker-homestead
192.168.45.12   docker-lappy
192.168.45.15   dock-servarr"

# Current node
CURRENT_NODE="dock-servarr"

echo "=== Docker Swarm Hosts Configuration ==="
echo "This script will update /etc/hosts on all swarm nodes"
echo ""

# Function to update hosts file locally
update_local_hosts() {
    echo "Updating hosts on local node (dock-servarr)..."
    
    # Backup
    sudo cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d-%H%M%S)
    echo "  Backup created: /etc/hosts.backup.$(date +%Y%m%d-%H%M%S)"
    
    # Check if our block already exists
    if grep -q "Docker Swarm Cluster (192.168.45.0/24 network)" /etc/hosts; then
        echo "  Swarm hosts already configured on local node"
    else
        # Add the block
        echo "$HOSTS_BLOCK" | sudo tee -a /etc/hosts > /dev/null
        echo "  Added swarm hosts to /etc/hosts"
    fi
}

# Function to update hosts file on remote node
update_remote_hosts() {
    local node=$1
    local ip=$2
    
    echo "Updating hosts on $node ($ip)..."
    
    # Test SSH connectivity first
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$ip "echo 'SSH OK'" > /dev/null 2>&1; then
        echo "  ERROR: Cannot SSH to $node at $ip"
        return 1
    fi
    
    # Backup on remote
    ssh root@$ip "cp /etc/hosts /etc/hosts.backup.\$(date +%Y%m%d-%H%M%S)"
    echo "  Backup created on $node"
    
    # Check and add entries
    if ssh root@$ip "grep -q 'Docker Swarm Cluster (192.168.45.0/24 network)' /etc/hosts"; then
        echo "  Swarm hosts already configured on $node"
    else
        # Add the block
        ssh root@$ip "echo '$HOSTS_BLOCK' >> /etc/hosts"
        echo "  Added swarm hosts to $node"
    fi
}

# Main execution
echo -e "\nStep 1: Updating local node..."
update_local_hosts

echo -e "\nStep 2: Updating remote nodes..."
for node in "${!NODES[@]}"; do
    if [[ "$node" != "$CURRENT_NODE" ]]; then
        update_remote_hosts "$node" "${NODES[$node]}"
    fi
done

# Verify connectivity
echo -e "\nStep 3: Verifying hostname resolution..."
echo "From dock-servarr (local):"
for target in docker-swarm docker-homestead docker-lappy; do
    if ping -c 1 -W 1 $target > /dev/null 2>&1; then
        echo "  ✓ $target is reachable"
    else
        echo "  ✗ $target is NOT reachable"
    fi
done

echo -e "\nConfiguration complete!"
echo "You can test with: ping docker-homestead"
