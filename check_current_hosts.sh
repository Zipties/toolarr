#!/bin/bash

echo "=== Current Hosts Configuration Check ==="
echo ""

echo "1. Local /etc/hosts entries:"
echo "   Existing docker-related entries:"
grep -E "(docker|swarm)" /etc/hosts | grep -v "^#" || echo "   None found"
echo ""
echo "   Commented docker-related entries:"
grep -E "(docker|swarm)" /etc/hosts | grep "^#" || echo "   None found"

echo -e "\n2. Current hostname resolution tests:"
for host in docker-swarm docker-homestead docker-lappy dock-servarr; do
    if getent hosts $host > /dev/null 2>&1; then
        ip=$(getent hosts $host | awk '{print $1}')
        echo "   $host resolves to $ip"
    else
        echo "   $host does NOT resolve"
    fi
done

echo -e "\n3. SSH connectivity to other nodes:"
echo "   Testing docker-homestead (192.168.45.11)..."
if timeout 3 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@192.168.45.11 "hostname" > /dev/null 2>&1; then
    echo "   ✓ Can SSH to docker-homestead"
else
    echo "   ✗ Cannot SSH to docker-homestead"
fi

echo "   Testing docker-lappy (192.168.45.12)..."
if timeout 3 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@192.168.45.12 "hostname" > /dev/null 2>&1; then
    echo "   ✓ Can SSH to docker-lappy"
else
    echo "   ✗ Cannot SSH to docker-lappy"
fi

echo -e "\n4. Docker Swarm node status:"
docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.ManagerStatus}}"
