# CMSVS Development-to-Production Workflow Guide

## 🎯 Overview
This guide will help you safely develop, test, and deploy improvements to your CMSVS application.

## 📁 Step 1: Set Up Development Environment

### 1.1 Create Development Branch
```bash
# Navigate to your project directory
cd C:\Users\Salem Almannai\Desktop\vscode\cmsvs

# Create and switch to development branch
git checkout -b development

# Push development branch to GitHub
git push -u origin development
```

### 1.2 Set Up Local Development Environment
```bash
# Copy production environment file for development
cp .env.production .env.development

# Edit .env.development for local development
# Change these settings:
# DEBUG=True
# ENVIRONMENT=development
# DATABASE_URL=postgresql://username:password@localhost:5432/cmsvs_dev
# FORCE_HTTPS=False
# SECURITY_HEADERS_ENABLED=False
```

### 1.3 Run Development Server Locally
```bash
# Start development environment
docker-compose -f docker-compose.yml up -d

# Or for development with hot reload
docker-compose -f docker-compose.development.yml up -d
```

## 🔧 Step 2: Development Workflow

### 2.1 Making Changes
1. **Always work on the development branch**
2. **Make small, focused changes**
3. **Test each change locally**
4. **Commit frequently with clear messages**

```bash
# Make your changes to code files
# Test the changes locally

# Stage your changes
git add .

# Commit with descriptive message
git commit -m "Fix: Improve login form validation"

# Push to development branch
git push origin development
```

### 2.2 Testing Your Changes
```bash
# Run local tests
docker-compose exec app python -m pytest

# Check application logs
docker-compose logs app

# Test in browser at http://localhost:8000
```

## 🚀 Step 3: Deployment to Production

### 3.1 Prepare for Deployment
```bash
# Switch to main branch
git checkout main

# Merge development changes
git merge development

# Push to main branch
git push origin main
```

### 3.2 Deploy to Production Server
```bash
# Connect to production server
ssh -i "C:\Users\Salem Almannai\.ssh\cmsvs_deploy_key_ed25519" root@91.99.118.65

# Navigate to application directory
cd /opt/cmsvs

# Pull latest changes
git pull origin main

# Rebuild and restart application
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps
```

## ⚠️ Safety Guidelines

### Before Making Changes:
1. **Always backup your database**
2. **Work on development branch only**
3. **Test locally before deploying**
4. **Keep production environment file secure**

### Emergency Rollback:
```bash
# If something goes wrong, rollback to previous version
git log --oneline  # Find previous working commit
git checkout <previous-commit-hash>
# Redeploy using Step 3.2
```

## 📝 Common Development Tasks

### Adding New Features:
1. Create feature branch: `git checkout -b feature/new-feature`
2. Develop and test locally
3. Merge to development: `git checkout development && git merge feature/new-feature`
4. Test on development
5. Deploy to production using Step 3

### Fixing Bugs:
1. Create bugfix branch: `git checkout -b bugfix/fix-issue`
2. Fix and test locally
3. Follow same merge process as features

### Frontend Changes:
1. Edit HTML templates in `app/templates/`
2. Edit CSS in `app/static/css/`
3. Edit JavaScript in `app/static/js/`
4. Test in browser locally
5. Deploy using standard process

## 🔍 Monitoring Production

### Check Application Health:
```bash
# Check container status
docker-compose -f docker-compose.production.yml ps

# Check application logs
docker-compose -f docker-compose.production.yml logs --tail=50 app

# Check database status
docker-compose -f docker-compose.production.yml logs --tail=20 db
```

### Access Production Database (if needed):
```bash
# Connect to production database
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db
```

## 📞 Getting Help

If you encounter issues:
1. Check application logs first
2. Verify all containers are healthy
3. Test the same changes locally
4. Ask for help with specific error messages

## 🎯 Next Steps

1. Set up development environment (Step 1)
2. Make a small test change
3. Practice the deployment workflow
4. Start developing your improvements!
