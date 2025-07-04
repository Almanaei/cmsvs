#!/usr/bin/env python3
"""
Production Deployment Script for CMSVS Internal System
This script helps prepare and deploy the application to production
"""

import os
import sys
import subprocess
import secrets
import shutil
from pathlib import Path
from typing import List, Dict, Any
import argparse


class ProductionDeployer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_production = self.project_root / ".env.production"
        self.env_file = self.project_root / ".env"
        
    def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
    
    def check_prerequisites(self) -> List[str]:
        """Check if all prerequisites are met"""
        issues = []
        
        # Check if Docker is installed
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("Docker is not installed or not accessible")
        
        # Check if Docker Compose is installed
        try:
            subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            issues.append("Docker Compose is not installed or not accessible")
        
        # Check if production env file exists
        if not self.env_production.exists():
            issues.append(".env.production file not found")
        
        return issues
    
    def setup_production_env(self, domain: str = None, admin_email: str = None, 
                           admin_password: str = None, db_password: str = None) -> bool:
        """Set up production environment file with secure values"""
        try:
            if not self.env_production.exists():
                print("❌ .env.production file not found")
                return False
            
            # Read the production template
            with open(self.env_production, 'r') as f:
                content = f.read()
            
            # Generate secure values
            secret_key = self.generate_secret_key()
            db_password = db_password or secrets.token_urlsafe(16)
            admin_password = admin_password or secrets.token_urlsafe(12)
            
            # Replace placeholder values
            replacements = {
                'CHANGE_THIS_TO_A_STRONG_SECRET_KEY_IN_PRODUCTION_AT_LEAST_32_CHARACTERS_LONG': secret_key,
                'CHANGE_THIS_PASSWORD': db_password,
                'CHANGE_THIS_STRONG_PASSWORD_IN_PRODUCTION': admin_password,
                'CHANGE_THIS_EMAIL_PASSWORD': secrets.token_urlsafe(12),
                'yourdomain.com': domain or 'localhost',
                'www.yourdomain.com': f'www.{domain}' if domain else 'localhost',
                'your-server-ip': '127.0.0.1',
                'admin@yourcompany.com': admin_email or 'admin@company.com',
                'noreply@yourcompany.com': f'noreply@{domain}' if domain else 'noreply@company.com',
                'smtp.yourcompany.com': f'smtp.{domain}' if domain else 'smtp.company.com'
            }
            
            for old, new in replacements.items():
                content = content.replace(old, new)
            
            # Write the updated content
            with open(self.env_production, 'w') as f:
                f.write(content)
            
            print("✅ Production environment configured successfully")
            print(f"🔑 Generated secret key: {secret_key[:10]}...")
            print(f"🔐 Generated admin password: {admin_password}")
            print(f"🗄️  Generated database password: {db_password}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up production environment: {e}")
            return False
    
    def update_docker_compose_production(self, db_password: str) -> bool:
        """Update docker-compose.yml for production"""
        try:
            compose_file = self.project_root / "docker-compose.yml"
            compose_prod_file = self.project_root / "docker-compose.production.yml"
            
            # Read the original compose file
            with open(compose_file, 'r') as f:
                content = f.read()
            
            # Update for production
            content = content.replace('your-secret-key-change-this-in-production', self.generate_secret_key())
            content = content.replace('cmsvs_password', db_password)
            content = content.replace('admin123', secrets.token_urlsafe(12))
            content = content.replace('"False"', '"True"')  # Set DEBUG to False
            
            # Add production-specific configurations
            production_additions = """
    # Production-specific configurations
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M"""
            
            # Write production compose file
            with open(compose_prod_file, 'w') as f:
                f.write(content)
            
            print("✅ Production Docker Compose configuration created")
            return True
            
        except Exception as e:
            print(f"❌ Error updating Docker Compose: {e}")
            return False
    
    def create_nginx_config(self, domain: str = None) -> bool:
        """Create Nginx configuration for reverse proxy"""
        try:
            nginx_dir = self.project_root / "nginx"
            nginx_dir.mkdir(exist_ok=True)
            
            domain = domain or "localhost"
            
            nginx_config = f"""
server {{
    listen 80;
    server_name {domain} www.{domain};
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain} www.{domain};
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/{domain}.crt;
    ssl_certificate_key /etc/ssl/private/{domain}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Client Settings
    client_max_body_size 50M;
    
    # Proxy to FastAPI application
    location / {{
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
    
    # Static files (if served by Nginx)
    location /static/ {{
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    # Health check endpoint
    location /health {{
        access_log off;
        proxy_pass http://app:8000/health;
    }}
}}
"""
            
            with open(nginx_dir / "nginx.conf", 'w') as f:
                f.write(nginx_config)
            
            print("✅ Nginx configuration created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating Nginx config: {e}")
            return False
    
    def create_systemd_service(self) -> bool:
        """Create systemd service file for production deployment"""
        try:
            service_content = f"""[Unit]
Description=CMSVS Internal System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=cmsvs
Group=cmsvs
WorkingDirectory={self.project_root}
Environment=ENVIRONMENT=production
ExecStart=/usr/bin/python3 {self.project_root}/run.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cmsvs

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={self.project_root}/uploads {self.project_root}/logs

[Install]
WantedBy=multi-user.target
"""
            
            service_file = self.project_root / "cmsvs.service"
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            print("✅ Systemd service file created")
            print(f"📝 To install: sudo cp {service_file} /etc/systemd/system/")
            print("📝 To enable: sudo systemctl enable cmsvs")
            print("📝 To start: sudo systemctl start cmsvs")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating systemd service: {e}")
            return False
    
    def run_security_check(self) -> List[str]:
        """Run security checks on the configuration"""
        issues = []
        
        try:
            # Check if production env file has secure values
            if self.env_production.exists():
                with open(self.env_production, 'r') as f:
                    content = f.read()
                
                if "CHANGE_THIS" in content:
                    issues.append("Production environment file contains placeholder values")
                
                if "DEBUG=True" in content:
                    issues.append("DEBUG mode is enabled in production")
                
                if "localhost" in content and "DATABASE_URL" in content:
                    issues.append("Database URL uses localhost in production")
            
            # Check file permissions
            sensitive_files = [".env", ".env.production"]
            for file in sensitive_files:
                file_path = self.project_root / file
                if file_path.exists():
                    stat = file_path.stat()
                    if stat.st_mode & 0o077:  # Check if group/other have any permissions
                        issues.append(f"{file} has overly permissive permissions")
        
        except Exception as e:
            issues.append(f"Error during security check: {e}")
        
        return issues
    
    def deploy(self, domain: str = None, admin_email: str = None, 
               admin_password: str = None, db_password: str = None) -> bool:
        """Main deployment function"""
        print("🚀 Starting CMSVS Production Deployment")
        print("=" * 50)
        
        # Check prerequisites
        print("🔍 Checking prerequisites...")
        issues = self.check_prerequisites()
        if issues:
            print("❌ Prerequisites not met:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        print("✅ Prerequisites check passed")
        
        # Set up production environment
        print("\n🔧 Setting up production environment...")
        if not self.setup_production_env(domain, admin_email, admin_password, db_password):
            return False
        
        # Create Nginx configuration
        print("\n🌐 Creating Nginx configuration...")
        self.create_nginx_config(domain)
        
        # Create systemd service
        print("\n⚙️  Creating systemd service...")
        self.create_systemd_service()
        
        # Run security check
        print("\n🔒 Running security checks...")
        security_issues = self.run_security_check()
        if security_issues:
            print("⚠️  Security issues found:")
            for issue in security_issues:
                print(f"  - {issue}")
        else:
            print("✅ Security checks passed")
        
        print("\n🎉 Production deployment preparation complete!")
        print("\n📋 Next steps:")
        print("1. Review the generated .env.production file")
        print("2. Set up SSL certificates")
        print("3. Configure your domain DNS")
        print("4. Run: docker-compose -f docker-compose.production.yml up -d")
        print("5. Set up automated backups")
        print("6. Configure monitoring")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Deploy CMSVS to production")
    parser.add_argument("--domain", help="Production domain name")
    parser.add_argument("--admin-email", help="Admin email address")
    parser.add_argument("--admin-password", help="Admin password (will be generated if not provided)")
    parser.add_argument("--db-password", help="Database password (will be generated if not provided)")
    parser.add_argument("--check-only", action="store_true", help="Only run checks without deployment")
    
    args = parser.parse_args()
    
    deployer = ProductionDeployer()
    
    if args.check_only:
        print("🔍 Running production readiness checks...")
        issues = deployer.check_prerequisites()
        security_issues = deployer.run_security_check()
        
        all_issues = issues + security_issues
        if all_issues:
            print("❌ Issues found:")
            for issue in all_issues:
                print(f"  - {issue}")
            return 1
        else:
            print("✅ All checks passed - ready for production!")
            return 0
    
    success = deployer.deploy(
        domain=args.domain,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        db_password=args.db_password
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
