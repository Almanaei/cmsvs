#!/bin/bash
# Setup required directories for Docker Compose

set -e

echo "🔧 Setting up CMSVS directory structure..."

# Create data directories
mkdir -p data/{postgres,redis,uploads,logs,prometheus}
mkdir -p secrets
mkdir -p ssl
mkdir -p config/{nginx,redis}
mkdir -p backups/db

# Set proper permissions
chmod 755 data
chmod 700 secrets
chmod 755 ssl
chmod 755 config
chmod 755 backups

# Create subdirectory permissions
chmod 755 data/postgres
chmod 755 data/redis
chmod 777 data/uploads
chmod 777 data/logs
chmod 755 data/prometheus

echo "📁 Directory structure created:"
echo "  data/"
echo "    ├── postgres/"
echo "    ├── redis/"
echo "    ├── uploads/"
echo "    ├── logs/"
echo "    └── prometheus/"
echo "  secrets/"
echo "  ssl/"
echo "  config/"
echo "    ├── nginx/"
echo "    └── redis/"
echo "  backups/"
echo "    └── db/"

echo "✅ Directory setup completed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Copy .env.example to .env and update values"
echo "2. Create secret files in secrets/ directory"
echo "3. Add SSL certificates to ssl/ directory (if using HTTPS)"
echo "4. Run: docker compose up -d"
