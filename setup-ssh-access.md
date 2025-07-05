# 🔑 SSH Access Setup for CMSVS Deployment

## Current Situation
- ✅ Server is reachable at `91.99.118.65`
- ❌ SSH authentication is not configured
- 🔑 SSH key has been generated: `~/.ssh/cmsvs_deploy_key`

## Your SSH Public Key
Copy this public key to your server:

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCmBuY3P+ER+2mHke71LliK8ITXWfY14JdJW5+JftbZsCIaURIADKdN2iAW4HacGSIOVq+6+UemHNeb0J31YdakKdsXddZ4EzmDi1g8Mb+BuU37y8GMQFHg9vbO8ieFvuhk0zp1dh/wVVmh9RdP9f/WDy42TJrZw4Y/susCHef3VkSwjHFDBSget/qQFuNvPKDY8NNUTDapbKh8ZfJIq4OYH/HktyFFpRUZS60GzC8MnsbpWY853X32437R7OGHBSkZzYoHjtmgDoF9Dpx/PewuyXY6p+QyOEqkIe9sVHjx/q28zQdV+WLBsLkAnZaZpz8Qn65H1ZFCtQ8eo6d9jAZFuLUWz3T+11FujNf3ZQxBBeOBv1f9JD/IwsSaZjhb/f675Zydep+bjsLO4M0VW6szHUAkYJmCBNbQ7ZIqs1Hh1qPNB9MwzavcxvUyDTT68e7SEUdijb6Glb7FCzHAD6Z+9H7ZDF/4inBBufxwAnXOwiF3SWJUZJg2bt4p0xoQ2WRVmSN/hgUHDXmDz+yjZYgSF9Dy5t4XabeqXNHHU43xdbTmN8SA5z/HvYGcGSxWuC2xSttqn4Jsj+7EsfsEmJB1R+p0pq/kxWlI990txkoB3ZRpMXPuDIIlcEzSxvkmk+cXqbVtR4Ya/TUzkg/oE+WtcGFf7u6X5nTkuA+iTPCbX3/+8jw== Salem Almannai@LTTC-C9PJ893
```

## Setup Options

### Option 1: Using Server Control Panel (Recommended)

If you have access to a control panel (like cPanel, Plesk, or cloud provider dashboard):

1. **Log into your server control panel**
2. **Navigate to SSH Keys section**
3. **Add the public key above**
4. **Save the configuration**

### Option 2: Using Password Authentication (Temporary)

If you know the root password for your server:

1. **Connect with password:**
   ```bash
   ssh root@91.99.118.65
   ```

2. **Create SSH directory:**
   ```bash
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   ```

3. **Add your public key:**
   ```bash
   echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCmBuY3P+ER+2mHke71LliK8ITXWfY14JdJW5+JftbZsCIaURIADKdN2iAW4HacGSIOVq+6+UemHNeb0J31YdakKdsXddZ4EzmDi1g8Mb+BuU37y8GMQFHg9vbO8ieFvuhk0zp1dh/wVVmh9RdP9f/WDy42TJrZw4Y/susCHef3VkSwjHFDBSget/qQFuNvPKDY8NNUTDapbKh8ZfJIq4OYH/HktyFFpRUZS60GzC8MnsbpWY853X32437R7OGHBSkZzYoHjtmgDoF9Dpx/PewuyXY6p+QyOEqkIe9sVHjx/q28zQdV+WLBsLkAnZaZpz8Qn65H1ZFCtQ8eo6d9jAZFuLUWz3T+11FujNf3ZQxBBeOBv1f9JD/IwsSaZjhb/f675Zydep+bjsLO4M0VW6szHUAkYJmCBNbQ7ZIqs1Hh1qPNB9MwzavcxvUyDTT68e7SEUdijb6Glb7FCzHAD6Z+9H7ZDF/4inBBufxwAnXOwiF3SWJUZJg2bt4p0xoQ2WRVmSN/hgUHDXmDz+yjZYgSF9Dy5t4XabeqXNHHU43xdbTmN8SA5z/HvYGcGSxWuC2xSttqn4Jsj+7EsfsEmJB1R+p0pq/kxWlI990txkoB3ZRpMXPuDIIlcEzSxvkmk+cXqbVtR4Ya/TUzkg/oE+WtcGFf7u6X5nTkuA+iTPCbX3/+8jw== Salem Almannai@LTTC-C9PJ893" >> ~/.ssh/authorized_keys
   ```

4. **Set proper permissions:**
   ```bash
   chmod 600 ~/.ssh/authorized_keys
   ```

5. **Exit and test SSH key access:**
   ```bash
   exit
   ssh -i ~/.ssh/cmsvs_deploy_key root@91.99.118.65
   ```

### Option 3: Contact Your Hosting Provider

If you don't have direct access:

1. **Contact your hosting provider**
2. **Request SSH key access**
3. **Provide them with the public key above**
4. **Ask them to add it to the root user's authorized_keys**

## Testing SSH Access

Once you've added the SSH key, test the connection:

```bash
ssh -i ~/.ssh/cmsvs_deploy_key root@91.99.118.65 "echo 'SSH access successful!'"
```

If this works, you'll see: `SSH access successful!`

## Alternative: Password-Based Deployment

If SSH key setup is not possible right now, I can modify the deployment script to use password authentication:

1. **Install sshpass** (for password authentication):
   ```bash
   # On Windows with Git Bash, you might need to install this separately
   # Or use WSL (Windows Subsystem for Linux)
   ```

2. **Use password authentication** (less secure but works):
   ```bash
   ssh root@91.99.118.65  # You'll be prompted for password
   ```

## Next Steps

1. **Choose one of the setup options above**
2. **Test SSH access**
3. **Run the deployment script:**
   ```bash
   ./deploy-production.sh
   ```

## Troubleshooting

### If SSH key doesn't work:
- Check file permissions: `chmod 600 ~/.ssh/cmsvs_deploy_key`
- Verify the key was added correctly on the server
- Try connecting with verbose output: `ssh -v -i ~/.ssh/cmsvs_deploy_key root@91.99.118.65`

### If you get "Permission denied":
- The public key might not be properly added to the server
- The server might not allow root login (try with another user)
- Password authentication might be disabled

### If you need help:
- Let me know which option you're trying
- Share any error messages you encounter
- I can help modify the deployment approach

---

**Once SSH access is working, the deployment script will handle everything else automatically!**
