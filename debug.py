import sys
print("--- sys.path ---")
print(sys.path)
print("--- end sys.path ---")

try:
    import karakeep
    print("Successfully imported karakeep")
except ImportError as e:
    print(f"Failed to import karakeep: {e}")
