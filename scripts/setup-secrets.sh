#!/bin/bash
# Setup secrets for production deployment
# This script creates secure secrets for Docker Compose

set -e

SECRETS_DIR="./secrets"
ENV_PROD_FILE=".env.production"

# Create secrets directory
mkdir -p "${SECRETS_DIR}"

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to generate secret key
generate_secret_key() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

echo "Setting up production secrets..."

# Generate database password
if [ ! -f "${SECRETS_DIR}/db_password.txt" ]; then
    DB_PASSWORD=$(generate_password)
    echo "${DB_PASSWORD}" > "${SECRETS_DIR}/db_password.txt"
    chmod 600 "${SECRETS_DIR}/db_password.txt"
    echo "✅ Database password generated"
else
    DB_PASSWORD=$(cat "${SECRETS_DIR}/db_password.txt")
    echo "✅ Database password already exists"
fi

# Generate secret key
if [ ! -f "${SECRETS_DIR}/secret_key.txt" ]; then
    SECRET_KEY=$(generate_secret_key)
    echo "${SECRET_KEY}" > "${SECRETS_DIR}/secret_key.txt"
    chmod 600 "${SECRETS_DIR}/secret_key.txt"
    echo "✅ Secret key generated"
else
    SECRET_KEY=$(cat "${SECRETS_DIR}/secret_key.txt")
    echo "✅ Secret key already exists"
fi

# Generate admin password
if [ ! -f "${SECRETS_DIR}/admin_password.txt" ]; then
    ADMIN_PASSWORD=$(generate_password)
    echo "${ADMIN_PASSWORD}" > "${SECRETS_DIR}/admin_password.txt"
    chmod 600 "${SECRETS_DIR}/admin_password.txt"
    echo "✅ Admin password generated"
else
    ADMIN_PASSWORD=$(cat "${SECRETS_DIR}/admin_password.txt")
    echo "✅ Admin password already exists"
fi

# Generate Redis password
if [ ! -f "${SECRETS_DIR}/redis_password.txt" ]; then
    REDIS_PASSWORD=$(generate_password)
    echo "${REDIS_PASSWORD}" > "${SECRETS_DIR}/redis_password.txt"
    chmod 600 "${SECRETS_DIR}/redis_password.txt"
    echo "✅ Redis password generated"
else
    REDIS_PASSWORD=$(cat "${SECRETS_DIR}/redis_password.txt")
    echo "✅ Redis password already exists"
fi

# Set proper permissions on secrets directory
chmod 700 "${SECRETS_DIR}"

# Create .env file for Docker Compose
cat > .env.docker << EOF
# Docker Compose environment variables
DB_PASSWORD=${DB_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
EOF

echo ""
echo "🔐 Production secrets have been generated:"
echo "   - Database password: ${SECRETS_DIR}/db_password.txt"
echo "   - Secret key: ${SECRETS_DIR}/secret_key.txt"
echo "   - Admin password: ${SECRETS_DIR}/admin_password.txt"
echo "   - Redis password: ${SECRETS_DIR}/redis_password.txt"
echo ""
echo "📝 Important notes:"
echo "   - Keep these files secure and never commit them to version control"
echo "   - Admin password: ${ADMIN_PASSWORD}"
echo "   - Database password: ${DB_PASSWORD}"
echo ""
echo "🚀 You can now run: docker-compose -f docker-compose.production.yml up -d"
