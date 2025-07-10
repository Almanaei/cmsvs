#!/usr/bin/env python3
"""
VAPID Key Generator for CMSVS Push Notifications
Generates VAPID public and private keys for web push notifications
"""

import os
import sys

try:
    from pywebpush import webpush
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    import base64
except ImportError as e:
    print(f"Error: Missing required packages. Please install: pip install pywebpush cryptography")
    print(f"Import error: {e}")
    sys.exit(1)


def generate_vapid_keys():
    """Generate VAPID public and private keys"""
    try:
        # Generate private key
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        
        # Get private key in PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Get public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Convert to base64 URL-safe format for VAPID
        private_key_b64 = base64.urlsafe_b64encode(private_pem).decode('utf-8').rstrip('=')
        public_key_b64 = base64.urlsafe_b64encode(public_pem).decode('utf-8').rstrip('=')
        
        return private_key_b64, public_key_b64
        
    except Exception as e:
        print(f"Error generating VAPID keys: {e}")
        return None, None


def main():
    """Main function to generate and display VAPID keys"""
    print("🔑 CMSVS VAPID Key Generator")
    print("=" * 40)
    
    private_key, public_key = generate_vapid_keys()
    
    if private_key and public_key:
        print("\n✅ VAPID Keys Generated Successfully!")
        print("\n📋 Add these to your environment configuration:")
        print("-" * 50)
        print(f"VAPID_PRIVATE_KEY={private_key}")
        print(f"VAPID_PUBLIC_KEY={public_key}")
        print(f"VAPID_EMAIL=almananei90@gmail.com")
        print("-" * 50)
        
        # Save to .env files
        env_content = f"""
# VAPID Keys for Push Notifications
VAPID_PRIVATE_KEY={private_key}
VAPID_PUBLIC_KEY={public_key}
VAPID_EMAIL=almananei90@gmail.com
"""
        
        try:
            with open('.env.vapid', 'w') as f:
                f.write(env_content)
            print(f"\n💾 Keys saved to .env.vapid file")
        except Exception as e:
            print(f"\n⚠️  Could not save to file: {e}")
        
        print("\n📝 Next steps:")
        print("1. Add these environment variables to your .env.production file")
        print("2. Update your Docker compose configuration")
        print("3. Restart your application")
        
    else:
        print("\n❌ Failed to generate VAPID keys")
        sys.exit(1)


if __name__ == "__main__":
    main()
