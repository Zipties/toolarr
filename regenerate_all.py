#!/usr/bin/env python3
"""
Regenerate all auto-generated files (OpenAPI + MCP tools)
Run this script whenever you modify API endpoints
"""

import os
import sys

def main():
    """Regenerate OpenAPI spec and MCP tools"""
    print("🔄 Regenerating OpenAPI specification and MCP tools...")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: Run this script from the toolarr directory")
        sys.exit(1)
    
    # Run the OpenAPI generation (which now includes MCP generation)
    print("1. Generating OpenAPI specification...")
    os.system("python3 generate_openapi.py")
    
    print("\n2. Verifying generated files...")
    
    # Check generated files
    files_to_check = [
        "openapi.json",
        "openapi-chatgpt.json", 
        "mcp_tools_generated.py"
    ]
    
    all_good = True
    for file in files_to_check:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING")
            all_good = False
    
    if all_good:
        print("\n🎉 All files regenerated successfully!")
        print("\nNext steps:")
        print("  1. Restart your FastAPI server to load new MCP tools")
        print("  2. Test with: python3 test_mcp_direct.py")
        print("  3. Your Claude Desktop integration will automatically use the updated tools")
    else:
        print("\n❌ Some files failed to generate. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()