import json
import os
from main import app
from prune_openapi import prune_openapi_spec

def generate():
    """
    Generates the full OpenAPI schema from the FastAPI app,
    saves it, and then runs the pruning script.
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

if __name__ == "__main__":
    generate()
