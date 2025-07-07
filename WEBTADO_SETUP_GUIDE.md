# 🌐 www.webtado.live Setup Guide

Complete guide to set up your CMSVS project on the domain www.webtado.live

## 📋 Prerequisites

- ✅ Domain `webtado.live` registered and owned by you
- ✅ Server running at IP `91.99.118.65`
- ✅ CMSVS project already deployed on the server

## 🎯 Step-by-Step Setup

### **Step 1: Configure DNS Records**

**IMPORTANT:** You must do this first before running any scripts!

1. **Log into your domain registrar** (where you bought webtado.live)
2. **Find DNS Management** section
3. **Add these DNS records:**

```
Type: A
Name: @ (or webtado.live)
Value: 91.99.118.65
TTL: 3600

Type: A
Name: www
Value: 91.99.118.65
TTL: 3600
```

4. **Save changes** and wait for DNS propagation (can take up to 48 hours)

### **Step 2: Verify DNS Propagation**

Check if your domain points to the correct IP:

```bash
# Check from your local computer
nslookup www.webtado.live
# Should return: 91.99.118.65

# Or use online tools:
# https://www.whatsmydns.net/
# Enter: www.webtado.live
```

### **Step 3: Deploy Domain Configuration**

Once DNS is working, deploy the changes:

```bash
# 1. Push the domain configuration to production
git push origin main

# 2. Deploy to server
./deploy.sh
```

### **Step 4: Run Domain Setup Script**

Connect to your server and run the automated setup:

```bash
# Connect to server
ssh -i ~/.ssh/cmsvs_deploy_key_ed25519 root@91.99.118.65

# Navigate to project directory
cd /opt/cmsvs

# Pull latest changes
git pull origin main

# Run the domain setup script
./setup-webtado-domain.sh
```

The script will:
- ✅ Check DNS configuration
- ✅ Install SSL certificate tools
- ✅ Set up SSL certificate with Let's Encrypt
- ✅ Update Nginx configuration
- ✅ Update application settings
- ✅ Deploy the application
- ✅ Test the deployment

### **Step 5: Verify Your Website**

After setup completes, test your website:

1. **HTTP Access:** http://www.webtado.live
2. **HTTPS Access:** https://www.webtado.live
3. **Login Test:** Try logging in with your admin credentials

## 🔧 Manual Setup (If Script Fails)

If the automated script fails, you can set up manually:

### **Install SSL Certificate:**

```bash
# Install Certbot
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot certonly --standalone -d www.webtado.live -d webtado.live --email almananei90@gmail.com --agree-tos
```

### **Update Nginx Configuration:**

```bash
# Copy the domain configuration
cp /opt/cmsvs/nginx/conf.d/webtado.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/webtado.conf /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Restart Nginx
systemctl restart nginx
```

### **Update Application:**

```bash
# Restart the application with new settings
cd /opt/cmsvs
docker-compose -f docker-compose.production.yml restart
```

## 🔍 Troubleshooting

### **DNS Not Resolving**

```bash
# Check DNS propagation
dig www.webtado.live
nslookup www.webtado.live

# If not working, wait longer or contact domain registrar
```

### **SSL Certificate Failed**

```bash
# Try manual certificate request
certbot certonly --standalone -d www.webtado.live -d webtado.live

# Check if ports 80 and 443 are open
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

### **Website Not Loading**

```bash
# Check application status
docker-compose -f docker-compose.production.yml ps

# Check logs
docker-compose -f docker-compose.production.yml logs nginx
docker-compose -f docker-compose.production.yml logs app

# Restart services
docker-compose -f docker-compose.production.yml restart
```

### **Login Issues**

```bash
# Check application logs
docker-compose -f docker-compose.production.yml logs app

# Verify database connection
docker-compose -f docker-compose.production.yml exec app python -c "from app.database import get_db; print('DB OK')"
```

## 📊 Expected Results

After successful setup:

- ✅ **http://www.webtado.live** → Redirects to HTTPS
- ✅ **https://www.webtado.live** → Shows your CMSVS application
- ✅ **https://webtado.live** → Redirects to www.webtado.live
- ✅ **SSL Certificate** → Valid and trusted
- ✅ **Login System** → Works with existing credentials

## 🔐 Security Features

Your new domain setup includes:

- ✅ **SSL/TLS Encryption** (HTTPS)
- ✅ **HTTP to HTTPS Redirect**
- ✅ **Security Headers** (HSTS, CSP, etc.)
- ✅ **Secure Cookies**
- ✅ **Non-www to www Redirect**

## 🎯 Next Steps

After setup is complete:

1. **Test all functionality** on the new domain
2. **Update any bookmarks** to use www.webtado.live
3. **Update external integrations** if any
4. **Monitor SSL certificate expiration** (auto-renews)

## 📞 Support

If you encounter issues:

1. **Check the logs** first
2. **Verify DNS settings** with your registrar
3. **Ensure ports 80 and 443** are open on your server
4. **Contact support** with specific error messages

## 🎉 Congratulations!

Once complete, your CMSVS project will be live at:
**https://www.webtado.live** 🚀
