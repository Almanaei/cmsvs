#!/usr/bin/env python3
"""
Simple Database Connection Test for CMSVS Production Setup
Tests PostgreSQL connectivity and security without app dependencies
"""

import psycopg2
import sys
import time

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'cmsvs_db',
    'user': 'cmsvs_user',
    'password': 'TfEcqHm7OeQUxHoQDMRYGXsFm'
}

def test_basic_connection():
    """Test basic database connection"""
    print("🔌 Testing basic database connection...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL Version: {version}")
        
        # Test database exists
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"   Current Database: {current_db}")
        
        # Test user permissions
        cursor.execute("SELECT current_user;")
        current_user = cursor.fetchone()[0]
        print(f"   Current User: {current_user}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_security_settings():
    """Test database security configuration"""
    print("\n🔒 Testing security settings...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check password encryption method
        cursor.execute("SHOW password_encryption;")
        pwd_encryption = cursor.fetchone()[0]
        print(f"   Password Encryption: {pwd_encryption}")
        
        # Check SSL status
        cursor.execute("SHOW ssl;")
        ssl_status = cursor.fetchone()[0]
        print(f"   SSL Status: {ssl_status}")
        
        # Check connection limits
        cursor.execute("""
            SELECT rolname, rolconnlimit 
            FROM pg_roles 
            WHERE rolname = %s;
        """, (DB_CONFIG['user'],))
        
        result = cursor.fetchone()
        if result:
            print(f"   Connection Limit: {result[1]}")
        
        # Check database permissions
        cursor.execute("""
            SELECT has_database_privilege(%s, %s, 'CONNECT') as can_connect,
                   has_database_privilege(%s, %s, 'CREATE') as can_create;
        """, (DB_CONFIG['user'], DB_CONFIG['database'],
              DB_CONFIG['user'], DB_CONFIG['database']))
        
        perms = cursor.fetchone()
        print(f"   Can Connect: {perms[0]}")
        print(f"   Can Create: {perms[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Security check failed: {e}")
        return False

def test_performance_settings():
    """Test database performance configuration"""
    print("\n⚡ Testing performance settings...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check key performance settings
        performance_settings = [
            'shared_buffers',
            'effective_cache_size',
            'work_mem',
            'maintenance_work_mem',
            'max_connections'
        ]
        
        for setting in performance_settings:
            cursor.execute(f"SHOW {setting};")
            value = cursor.fetchone()[0]
            print(f"   {setting}: {value}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Performance check failed: {e}")
        return False

def test_extensions():
    """Test available extensions"""
    print("\n🔧 Testing database extensions...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check installed extensions
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            ORDER BY extname;
        """)
        
        extensions = cursor.fetchall()
        if extensions:
            print("   Installed Extensions:")
            for ext_name, ext_version in extensions:
                print(f"     - {ext_name} (v{ext_version})")
        else:
            print("   No extensions installed yet")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Extensions check failed: {e}")
        return False

def test_schemas():
    """Test database schemas"""
    print("\n📋 Testing database schemas...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check available schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        
        schemas = cursor.fetchall()
        if schemas:
            print("   Available Schemas:")
            for schema in schemas:
                print(f"     - {schema[0]}")
        else:
            print("   Only default schemas available")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Schema check failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 CMSVS Database Connection Test")
    print("=" * 50)
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    print("=" * 50)
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    if test_basic_connection():
        tests_passed += 1
    
    if test_security_settings():
        tests_passed += 1
    
    if test_performance_settings():
        tests_passed += 1
    
    if test_extensions():
        tests_passed += 1
    
    if test_schemas():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Database is ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
