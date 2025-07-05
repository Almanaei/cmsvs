#!/bin/bash
# Create secret files for Docker Compose

set -e

SECRETS_DIR="./secrets"

echo "🔐 Creating secret files for CMSVS..."

# Create secrets directory if it doesn't exist
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Generate random passwords if files don't exist
if [ ! -f "$SECRETS_DIR/db_password.txt" ]; then
    echo "Generating database password..."
    openssl rand -base64 32 > "$SECRETS_DIR/db_password.txt"
    chmod 600 "$SECRETS_DIR/db_password.txt"
    echo "✅ Database password created"
fi

if [ ! -f "$SECRETS_DIR/secret_key.txt" ]; then
    echo "Generating application secret key..."
    openssl rand -base64 64 > "$SECRETS_DIR/secret_key.txt"
    chmod 600 "$SECRETS_DIR/secret_key.txt"
    echo "✅ Application secret key created"
fi

if [ ! -f "$SECRETS_DIR/admin_password.txt" ]; then
    echo "Generating admin password..."
    openssl rand -base64 16 > "$SECRETS_DIR/admin_password.txt"
    chmod 600 "$SECRETS_DIR/admin_password.txt"
    echo "✅ Admin password created"
fi

echo ""
echo "🔐 Secret files created in $SECRETS_DIR/"
echo "📝 Generated passwords:"
echo "  Database password: $(cat $SECRETS_DIR/db_password.txt)"
echo "  Admin password: $(cat $SECRETS_DIR/admin_password.txt)"
echo ""
echo "⚠️  IMPORTANT: Save these passwords securely!"
echo "⚠️  The secret key is not displayed for security reasons."
echo ""
echo "✅ Secret creation completed successfully!"
