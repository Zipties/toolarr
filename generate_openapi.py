import json
import os
import subprocess
from main import app
from prune_openapi import prune_openapi_spec

def generate():
    """
    Generates the full OpenAPI schema from the FastAPI app,
    saves it, runs the pruning script, and generates MCP tools.
    """
    # Ensure we start fresh by deleting any old files
    for file_path in ["openapi.json", "openapi-chatgpt.json"]:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed old {file_path}")

    # Generate the full OpenAPI schema
    openapi_schema = app.openapi()
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("Successfully generated openapi.json")

    # Prune the schema for ChatGPT
    prune_openapi_spec()
    
    # Generate MCP tools from the pruned OpenAPI spec
    print("Generating MCP tools from OpenAPI specification...")
    try:
        result = subprocess.run(["python3", "generate_mcp_tools.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Successfully generated MCP tools")
        else:
            print(f"❌ MCP generation failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Error generating MCP tools: {e}")

if __name__ == "__main__":
    generate()
