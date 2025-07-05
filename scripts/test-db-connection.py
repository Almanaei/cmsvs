#!/usr/bin/env python3
"""
Database Connection and Security Testing Script for CMSVS
Tests PostgreSQL connectivity, security, and performance
"""

import sys
import os
import time
import psycopg2
from psycopg2 import sql
from pathlib import Path
import asyncio
import asyncpg

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

class DatabaseTester:
    def __init__(self):
        self.db_url = settings.database_url
        self.connection = None
        self.async_pool = None
        
    def parse_db_url(self):
        """Parse database URL components"""
        # postgresql://user:password@host:port/database
        url_parts = self.db_url.replace('postgresql://', '').split('/')
        auth_host = url_parts[0]
        database = url_parts[1] if len(url_parts) > 1 else 'cmsvs_db'
        
        auth, host_port = auth_host.split('@')
        user, password = auth.split(':')
        host, port = host_port.split(':')
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': int(port),
            'database': database
        }
    
    def test_basic_connection(self):
        """Test basic database connection"""
        print("🔌 Testing basic database connection...")
        
        try:
            db_params = self.parse_db_url()
            self.connection = psycopg2.connect(**db_params)
            cursor = self.connection.cursor()
            
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
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_security_settings(self):
        """Test database security configuration"""
        print("\n🔒 Testing security settings...")
        
        if not self.connection:
            print("❌ No database connection available")
            return False
        
        try:
            cursor = self.connection.cursor()
            
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
            """, (self.parse_db_url()['user'],))
            
            result = cursor.fetchone()
            if result:
                print(f"   Connection Limit: {result[1]}")
            
            # Check database permissions
            cursor.execute("""
                SELECT has_database_privilege(%s, %s, 'CONNECT') as can_connect,
                       has_database_privilege(%s, %s, 'CREATE') as can_create;
            """, (self.parse_db_url()['user'], self.parse_db_url()['database'],
                  self.parse_db_url()['user'], self.parse_db_url()['database']))
            
            perms = cursor.fetchone()
            print(f"   Can Connect: {perms[0]}")
            print(f"   Can Create: {perms[1]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Security check failed: {e}")
            return False
    
    def test_performance_settings(self):
        """Test database performance configuration"""
        print("\n⚡ Testing performance settings...")
        
        if not self.connection:
            print("❌ No database connection available")
            return False
        
        try:
            cursor = self.connection.cursor()
            
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
            
            return True
            
        except Exception as e:
            print(f"❌ Performance check failed: {e}")
            return False
    
    async def test_connection_pool(self):
        """Test connection pooling with asyncpg"""
        print("\n🏊 Testing connection pool...")
        
        try:
            db_params = self.parse_db_url()
            
            # Create connection pool
            self.async_pool = await asyncpg.create_pool(
                user=db_params['user'],
                password=db_params['password'],
                database=db_params['database'],
                host=db_params['host'],
                port=db_params['port'],
                min_size=settings.db_pool_size // 4,
                max_size=settings.db_pool_size,
                command_timeout=settings.db_pool_timeout
            )
            
            print(f"✅ Connection pool created successfully!")
            print(f"   Pool Size: {settings.db_pool_size}")
            print(f"   Max Overflow: {settings.db_max_overflow}")
            print(f"   Pool Timeout: {settings.db_pool_timeout}s")
            
            # Test pool performance
            start_time = time.time()
            
            async def test_query():
                async with self.async_pool.acquire() as conn:
                    return await conn.fetchval("SELECT 1")
            
            # Run multiple concurrent queries
            tasks = [test_query() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            print(f"   10 concurrent queries completed in {end_time - start_time:.3f}s")
            
            await self.async_pool.close()
            return True
            
        except Exception as e:
            print(f"❌ Connection pool test failed: {e}")
            return False
    
    def test_table_access(self):
        """Test access to application tables"""
        print("\n📋 Testing table access...")
        
        if not self.connection:
            print("❌ No database connection available")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Check if main tables exist (they might not exist yet)
            tables_to_check = ['users', 'requests', 'files', 'messages']
            
            for table in tables_to_check:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table,))
                
                exists = cursor.fetchone()[0]
                status = "✅" if exists else "⚠️ "
                print(f"   {status} Table '{table}': {'exists' if exists else 'not found (will be created by migration)'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Table access test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up connections"""
        if self.connection:
            self.connection.close()

async def main():
    """Main test function"""
    print("🔍 CMSVS Database Connection and Security Test")
    print("=" * 60)
    print(f"Database URL: {settings.database_url}")
    print("=" * 60)
    
    tester = DatabaseTester()
    
    try:
        # Run tests
        tests_passed = 0
        total_tests = 5
        
        if tester.test_basic_connection():
            tests_passed += 1
        
        if tester.test_security_settings():
            tests_passed += 1
        
        if tester.test_performance_settings():
            tests_passed += 1
        
        if await tester.test_connection_pool():
            tests_passed += 1
        
        if tester.test_table_access():
            tests_passed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All tests passed! Database is ready for production.")
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
    
    finally:
        tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
