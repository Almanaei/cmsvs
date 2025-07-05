# 🚀 CMSVS Development Quick Reference

## 📋 Essential Commands

### 🛠️ First Time Setup
```bash
# Set up development environment (run once)
./setup-development.sh
```

### 💻 Daily Development
```bash
# Start development environment
docker-compose -f docker-compose.development.yml up -d

# View application logs
docker-compose -f docker-compose.development.yml logs -f app

# Stop development environment
docker-compose -f docker-compose.development.yml down

# Restart after code changes
docker-compose -f docker-compose.development.yml restart app
```

### 🔄 Git Workflow
```bash
# Switch to development branch
git checkout development

# Make your changes, then:
git add .
git commit -m "Description of your changes"
git push origin development

# When ready to deploy:
git checkout main
git merge development
git push origin main
```

### 🚀 Deploy to Production
```bash
# Deploy to production (automated script)
./deploy.sh
```

## 📁 Important Files & Directories

### 🎨 Frontend Files
- **HTML Templates**: `app/templates/`
- **CSS Styles**: `app/static/css/`
- **JavaScript**: `app/static/js/`
- **Images**: `app/static/images/`

### 🔧 Backend Files
- **Main Application**: `app/main.py`
- **API Routes**: `app/routers/`
- **Database Models**: `app/models/`
- **Configuration**: `app/config.py`

### ⚙️ Configuration Files
- **Development**: `.env.development`
- **Production**: `.env.production`
- **Docker Dev**: `docker-compose.development.yml`
- **Docker Prod**: `docker-compose.production.yml`

## 🎯 Common Development Tasks

### 1. 🎨 Changing the Frontend
```bash
# Edit HTML templates
code app/templates/login.html

# Edit CSS styles
code app/static/css/style.css

# Edit JavaScript
code app/static/js/main.js

# Restart to see changes
docker-compose -f docker-compose.development.yml restart app
```

### 2. 🔧 Adding New Features
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make your changes
# Test locally at http://localhost:8000

# Commit changes
git add .
git commit -m "Add new feature: description"

# Merge to development
git checkout development
git merge feature/new-feature

# Test and deploy
./deploy.sh
```

### 3. 🐛 Fixing Bugs
```bash
# Create bugfix branch
git checkout -b bugfix/fix-issue

# Fix the bug
# Test the fix locally

# Commit and merge
git add .
git commit -m "Fix: description of bug fix"
git checkout development
git merge bugfix/fix-issue

# Deploy fix
./deploy.sh
```

### 4. 📊 Database Changes
```bash
# Access development database
docker-compose -f docker-compose.development.yml exec db psql -U cmsvs_user -d cmsvs_dev

# Reset development database
docker-compose -f docker-compose.development.yml down -v
docker-compose -f docker-compose.development.yml up -d
docker-compose -f docker-compose.development.yml exec app python init_db.py
```

## 🔍 Troubleshooting

### ❌ Application Not Starting
```bash
# Check container status
docker-compose -f docker-compose.development.yml ps

# Check logs for errors
docker-compose -f docker-compose.development.yml logs app

# Restart everything
docker-compose -f docker-compose.development.yml down
docker-compose -f docker-compose.development.yml up -d
```

### ❌ Database Connection Issues
```bash
# Check database container
docker-compose -f docker-compose.development.yml logs db

# Restart database
docker-compose -f docker-compose.development.yml restart db
```

### ❌ Changes Not Showing
```bash
# Clear browser cache (Ctrl+F5)
# Or restart app container
docker-compose -f docker-compose.development.yml restart app
```

## 🌐 URLs & Access

### 🖥️ Development
- **Application**: http://localhost:8000
- **Database**: localhost:5432
- **Redis**: localhost:6379

### 🚀 Production
- **Application**: http://91.99.118.65
- **SSH Access**: `ssh -i ~/.ssh/cmsvs_deploy_key_ed25519 root@91.99.118.65`

## 🔑 Login Credentials

### 💻 Development
- **Username**: admin
- **Email**: almananei90@gmail.com
- **Password**: admin123

### 🚀 Production
- **Username**: admin
- **Email**: almananei90@gmail.com
- **Password**: SecureAdmin2025!

## ⚠️ Safety Rules

1. **Always work on development branch**
2. **Test locally before deploying**
3. **Commit changes frequently**
4. **Use descriptive commit messages**
5. **Never edit production files directly**
6. **Always backup before major changes**

## 📞 Getting Help

If you encounter issues:
1. Check the logs first
2. Try restarting the containers
3. Check this reference guide
4. Ask for help with specific error messages

## 🎯 Next Steps

1. Run `./setup-development.sh` to get started
2. Make a small test change
3. Practice the deployment workflow
4. Start developing your improvements!
