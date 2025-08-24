#!/usr/bin/env python3
"""
Script to fix main.py by adding the emails router
"""
import os

def fix_main_py():
    """Add emails router to main.py"""
    
    main_py_path = "src/main.py"
    
    # Read the current file
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Add emails to the import
    if "from api import auth, users, gmail, workflows" in content:
        content = content.replace(
            "from api import auth, users, gmail, workflows",
            "from api import auth, users, gmail, workflows, emails"
        )
        print("✅ Added emails to imports")
    else:
        print("⚠️  Could not find import line to modify")
    
    # Add emails router inclusion
    if "app.include_router(workflows.router, tags=[\"workflows\"])" in content:
        content = content.replace(
            "app.include_router(workflows.router, tags=[\"workflows\"])",
            "app.include_router(workflows.router, tags=[\"workflows\"])\napp.include_router(emails.router, tags=[\"emails\"])"
        )
        print("✅ Added emails router inclusion")
    else:
        print("⚠️  Could not find workflows router line to modify")
    
    # Write the modified content back
    with open(main_py_path, 'w') as f:
        f.write(content)
    
    print("✅ main.py has been updated!")

if __name__ == "__main__":
    fix_main_py()

