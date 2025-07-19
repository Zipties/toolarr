import json

def prune_openapi_spec(input_file="openapi.json", output_file="openapi-chatgpt.json"):
    """
    Loads an OpenAPI spec, removes operations tagged with "internal-admin",
    and also removes any unreferenced schemas from the components section.
    """
    with open(input_file, "r") as f:
        spec = json.load(f)

    # --- Step 1: Prune paths based on tag ---
    paths_to_delete = []
    for path, path_item in spec.get("paths", {}).items():
        methods_to_delete = []
        for method, operation in path_item.items():
            if "internal-admin" in operation.get("tags", []):
                methods_to_delete.append(method)
        
        for method in methods_to_delete:
            del spec["paths"][path][method]

        if not spec["paths"][path]:
            paths_to_delete.append(path)

    for path in paths_to_delete:
        del spec["paths"][path]

    # --- Step 2: Prune unreferenced schemas ---
    
    # First, find all schema references ($ref) that are still in use
    used_schemas = set()
    
    # --- Always keep these essential schemas ---
    essential_schemas = {"HTTPValidationError", "ValidationError"}
    used_schemas.update(essential_schemas)
    
    def find_refs(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
                    schema_name = value.split("/")[-1]
                    used_schemas.add(schema_name)
                else:
                    find_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                find_refs(item)

    find_refs(spec.get("paths", {}))

    # Now, rebuild the schemas object with only the used schemas
    if "components" in spec and "schemas" in spec["components"]:
        all_schemas = spec["components"]["schemas"]
        pruned_schemas = {name: schema for name, schema in all_schemas.items() if name in used_schemas}
        spec["components"]["schemas"] = pruned_schemas

    with open(output_file, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"Successfully pruned spec and unreferenced schemas. Pruned spec saved to {output_file}")

if __name__ == "__main__":
    prune_openapi_spec()
