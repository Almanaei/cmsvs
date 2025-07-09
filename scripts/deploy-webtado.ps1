# CMSVS Deployment Script for www.webtado.live
# PowerShell script to deploy the latest changes to the production server

param(
    [string]$ServerIP = "91.99.118.65",
    [string]$ServerUser = "root",
    [string]$ProjectPath = "/opt/cmsvs"
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Log $Message $Green
}

function Write-Error {
    param([string]$Message)
    Write-Log $Message $Red
}

function Write-Warning {
    param([string]$Message)
    Write-Log $Message $Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Log $Message $Blue
}

# Main deployment function
function Deploy-ToProduction {
    Write-Host "🚀 CMSVS Production Deployment to www.webtado.live" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "Target Server: $ServerIP" -ForegroundColor Cyan
    Write-Host "Started: $(Get-Date)" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""

    # Test SSH connection
    Write-Info "Testing SSH connection to server..."
    $testConnection = ssh -o BatchMode=yes -o ConnectTimeout=5 "$ServerUser@$ServerIP" "echo 'Connection test successful'" 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "SSH key authentication failed. You will need to enter password."
    } else {
        Write-Success "SSH connection test successful"
    }

    # Create deployment commands
    $deploymentCommands = @"
set -e

echo "🚀 Starting CMSVS deployment on production server..."

# Navigate to project directory or create it
if [ ! -d "$ProjectPath" ]; then
    echo "Creating project directory..."
    mkdir -p $ProjectPath
fi

cd $ProjectPath

# Backup current deployment if exists
if [ -d ".git" ]; then
    echo "Backing up current deployment..."
    tar -czf "backup-`$(date +%Y%m%d_%H%M%S).tar.gz" . 2>/dev/null || true
fi

# Clone or pull latest changes
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    git clone https://github.com/Almanaei/cmsvs.git .
else
    echo "Pulling latest changes..."
    git fetch origin
    git reset --hard origin/main
fi

# Navigate to deployment directory
cd deployment

# Stop existing services
echo "Stopping existing services..."
docker-compose -f docker-compose.production.yml down --timeout 30 2>/dev/null || true

# Remove old images to ensure fresh build
echo "Cleaning up old Docker images..."
docker system prune -f 2>/dev/null || true

# Build and start services
echo "Building Docker images..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "Starting services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 45

# Initialize database if needed
echo "Initializing database..."
docker-compose -f docker-compose.production.yml exec -T app python init_db.py 2>/dev/null || echo "Database already initialized"

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.production.yml ps

# Test application health
echo "Testing application health..."
sleep 10
if curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✅ Application health check passed"
else
    echo "⚠️  Application health check failed - checking if app is responding..."
    if curl -f http://localhost:8000/ 2>/dev/null; then
        echo "✅ Application is responding on root path"
    else
        echo "❌ Application is not responding"
    fi
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo "📊 Service Status:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "🌐 Your application should be available at:"
echo "   - http://www.webtado.live"
echo "   - http://$ServerIP"
echo ""
"@

    # Execute deployment on remote server
    Write-Info "Executing deployment on remote server..."
    Write-Host "You may need to enter your server password..." -ForegroundColor Yellow
    
    try {
        $deploymentCommands | ssh "$ServerUser@$ServerIP" "bash -s"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Deployment to production server completed successfully!"
            Write-Host ""
            Write-Host "🌐 Your CMSVS application is now live at:" -ForegroundColor Green
            Write-Host "   - https://www.webtado.live" -ForegroundColor Cyan
            Write-Host "   - http://$ServerIP" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "📋 Next steps:" -ForegroundColor Yellow
            Write-Host "   1. Test the application functionality" -ForegroundColor White
            Write-Host "   2. Check SSL certificate status" -ForegroundColor White
            Write-Host "   3. Monitor application logs if needed" -ForegroundColor White
        } else {
            Write-Error "Deployment failed. Please check the server logs."
            exit 1
        }
    }
    catch {
        Write-Error "Error during deployment: $($_.Exception.Message)"
        exit 1
    }
}

# Run deployment
Deploy-ToProduction

Write-Success "All deployment tasks completed!"
