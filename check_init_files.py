#!/usr/bin/env python3
"""
Script to check and create missing __init__.py files in the project
"""

import os
import sys

def check_and_create_init_files():
    """Check for missing __init__.py files and create them"""
    
    # Directories that should have __init__.py files
    required_init_dirs = [
        'app',
        'app/models',
        'app/routes', 
        'app/services',
        'app/utils',
        'app/middleware'
    ]
    
    print("🔍 Checking for __init__.py files...")
    
    missing_files = []
    existing_files = []
    
    for dir_path in required_init_dirs:
        init_file = os.path.join(dir_path, '__init__.py')
        
        if os.path.exists(init_file):
            existing_files.append(init_file)
            print(f"✅ {init_file} - EXISTS")
        else:
            missing_files.append(init_file)
            print(f"❌ {init_file} - MISSING")
    
    # Create missing __init__.py files
    if missing_files:
        print(f"\n📝 Creating {len(missing_files)} missing __init__.py files...")
        
        for init_file in missing_files:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(init_file), exist_ok=True)
                
                # Create __init__.py with appropriate content
                dir_name = os.path.basename(os.path.dirname(init_file))
                content = f"# {dir_name.title()} package\n"
                
                # Add special content for utils package
                if 'utils' in init_file:
                    content += "\n# Explicitly import FileHandler to ensure it's available\nfrom .file_handler import FileHandler\n\n__all__ = ['FileHandler']\n"
                
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Created {init_file}")
                
            except Exception as e:
                print(f"❌ Failed to create {init_file}: {e}")
    else:
        print("\n✅ All required __init__.py files are present!")
    
    # Test imports
    print("\n🧪 Testing critical imports...")
    
    try:
        from app.utils.file_handler import FileHandler
        print("✅ from app.utils.file_handler import FileHandler - SUCCESS")
    except ImportError as e:
        print(f"❌ from app.utils.file_handler import FileHandler - FAILED: {e}")
        return False
    
    try:
        from app.utils import FileHandler as FH
        print("✅ from app.utils import FileHandler - SUCCESS")
    except ImportError as e:
        print(f"❌ from app.utils import FileHandler - FAILED: {e}")
        return False
    
    try:
        from app.services.request_service import RequestService
        print("✅ from app.services.request_service import RequestService - SUCCESS")
    except ImportError as e:
        print(f"❌ from app.services.request_service import RequestService - FAILED: {e}")
        return False
    
    print("\n🎉 All imports successful!")
    return True

if __name__ == "__main__":
    print("🚀 Python Package Structure Checker")
    print("=" * 40)
    
    success = check_and_create_init_files()
    
    if success:
        print("\n✅ All checks passed! The project structure is ready for deployment.")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please review the errors above.")
        sys.exit(1)
