# Local Development Setup Guide

This guide will help you set up the CMSVS application for local development and testing.

## Prerequisites

- Windows 10/11
- Docker Desktop installed
- Git (already installed)

## Quick Start (Recommended)

### Step 1: Start Docker Desktop
1. Open Docker Desktop from Start Menu or desktop icon
2. Wait for Docker Desktop to fully start (green icon in system tray)
3. You should see "Docker Desktop is running" in the system tray

### Step 2: Start Development Environment
1. Open Command Prompt or PowerShell in the project directory
2. Run the setup script:
   ```cmd
   start-development.bat
   ```

This script will:
- Check if Docker Desktop is running
- Stop any existing containers
- Build and start the development environment
- Show you the application URLs and credentials

### Step 3: Initialize Database
Once the containers are running, initialize the database:
```cmd
python init-development-db.py
```

### Step 4: Access the Application
- **Main Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/login
- **API Documentation**: http://localhost:8000/docs

**Default Admin Credentials:**
- Email: `almananei90@gmail.com`
- Password: `admin123`

## Manual Setup (Alternative)

If you prefer to run commands manually:

### 1. Start the Development Environment
```cmd
docker compose -f docker-compose.development.yml up --build -d
```

### 2. Check Container Status
```cmd
docker compose -f docker-compose.development.yml ps
```

### 3. View Logs
```cmd
docker compose -f docker-compose.development.yml logs -f
```

### 4. Stop the Environment
```cmd
docker compose -f docker-compose.development.yml down
```

## Testing the Logger Fix

Once the application is running:

1. Go to http://localhost:8000
2. Login with admin credentials
3. Navigate to "New Request" page
4. Try to create a new request
5. The logger error should be resolved

## Troubleshooting

### Docker Desktop Not Running
**Error**: `error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine...`

**Solution**: 
1. Start Docker Desktop
2. Wait for it to fully load (green icon in system tray)
3. Try again

### Port Already in Use
**Error**: `port is already allocated`

**Solution**:
```cmd
docker compose -f docker-compose.development.yml down
netstat -ano | findstr :8000
# Kill any process using port 8000 if needed
```

### Database Connection Issues
**Error**: `could not connect to server`

**Solution**:
1. Wait for PostgreSQL container to fully start (30-60 seconds)
2. Check container status: `docker compose -f docker-compose.development.yml ps`
3. Check database logs: `docker compose -f docker-compose.development.yml logs db`

### Application Not Loading
1. Check if all containers are running:
   ```cmd
   docker compose -f docker-compose.development.yml ps
   ```
2. Check application logs:
   ```cmd
   docker compose -f docker-compose.development.yml logs app
   ```

## Development Workflow

1. **Make Code Changes**: Edit files in your IDE
2. **Auto-Reload**: The application will automatically reload when you save changes
3. **View Logs**: Use `docker compose -f docker-compose.development.yml logs -f app`
4. **Database Changes**: Run `python init-development-db.py` if you modify models

## Services Overview

- **app**: FastAPI application (Port 8000)
- **db**: PostgreSQL database (Port 5432)
- **redis**: Redis cache (Port 6379)
- **nginx**: Reverse proxy (Port 80)

## Environment Files

- `.env.development`: Development-specific configuration
- `docker-compose.development.yml`: Development Docker setup

## Next Steps

After successful setup:
1. Test the request/new page to verify the logger fix
2. Make any additional changes needed
3. Deploy changes to production server

## Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Review container logs
3. Ensure Docker Desktop is running properly
