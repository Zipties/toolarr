#!/bin/bash
# Toolarr Quick Deploy Script

echo "🚀 Toolarr Quick Deploy"
echo "======================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys before proceeding!"
    echo "   Run: nano .env"
    exit 1
fi

# Check if docker swarm is initialized
if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
    echo "⚠️  Docker Swarm is not initialized!"
    echo "   Run: docker swarm init"
    exit 1
fi

# Check if network exists
if ! docker network ls | grep -q "traefik_public"; then
    echo "Creating traefik_public network..."
    docker network create -d overlay traefik_public
fi

# Deploy the stack
echo "Deploying Toolarr..."
docker stack deploy -c docker-compose.yml toolarr

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Check service status: docker service ls | grep toolarr"
echo "2. View logs: docker service logs toolarr_toolarr"
echo "3. Add to Open WebUI: http://toolarr:8000/openapi.json"
echo "   - Auth Type: Bearer Token"
echo "   - Token: Your TOOL_API_KEY from .env"
