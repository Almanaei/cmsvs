#!/bin/bash

# Fix Git issues on Windows
echo "🔧 Fixing Git issues..."

# Remove problematic files
echo "Removing problematic files..."
rm -f nul 2>/dev/null || del nul 2>/dev/null || true
rm -f NUL 2>/dev/null || del NUL 2>/dev/null || true

# Configure Git for Windows
echo "Configuring Git for Windows..."
git config core.autocrlf true
git config core.safecrlf false

# Reset staging area
echo "Resetting Git staging area..."
git reset

# Clean working directory
echo "Cleaning working directory..."
git clean -fd

# Check status
echo "Current Git status:"
git status

echo "✅ Git issues fixed! You can now run 'git add .' again."
