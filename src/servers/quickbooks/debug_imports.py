import os
import sys
import inspect
import site
import importlib
import importlib.util

# Print Python version
print(f"Python version: {sys.version}")

# Print current working directory
print(f"Current directory: {os.getcwd()}")

# Print sys.path
print("\nSystem path:")
for p in sys.path:
    print(f"  {p}")

# Get site-packages directories
print("\nSite-packages directories:")
for p in site.getsitepackages():
    print(f"  {p}")

# Try to import the quickbooks module
print("\nTrying to import quickbooks:")
try:
    import quickbooks

    print(f"Success! quickbooks module loaded from: {quickbooks.__file__}")

    # Try to import Customer
    try:
        from quickbooks.objects.customer import Customer

        print(f"Success! Customer imported from: {inspect.getfile(Customer)}")
    except ImportError as e:
        print(f"Failed to import Customer: {e}")

        # List contents of quickbooks module
        print("\nContents of quickbooks module:")
        print(dir(quickbooks))

        # Check if objects exists
        if hasattr(quickbooks, "objects"):
            print("\nContents of quickbooks.objects:")
            print(dir(quickbooks.objects))
        else:
            print("\nquickbooks.objects not found")

            # Check if the objects directory exists
            qb_dir = os.path.dirname(quickbooks.__file__)
            obj_dir = os.path.join(qb_dir, "objects")
            print(f"Checking for objects directory at: {obj_dir}")
            if os.path.exists(obj_dir):
                print(f"Directory exists, contents: {os.listdir(obj_dir)}")

                # Try manual import
                spec = importlib.util.spec_from_file_location(
                    "quickbooks.objects", os.path.join(obj_dir, "__init__.py")
                )
                if spec and spec.loader:
                    objects_module = importlib.util.module_from_spec(spec)
                    sys.modules["quickbooks.objects"] = objects_module
                    spec.loader.exec_module(objects_module)
                    print("Manually imported quickbooks.objects")
                    print(f"Contents: {dir(objects_module)}")
            else:
                print("Directory does not exist")

except ImportError as e:
    print(f"Failed to import quickbooks: {e}")
