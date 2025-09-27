#!/usr/bin/env python3
"""
Fix all effects service handlers to use ServiceRequest instead of Dict[str, Any]
"""
import re

# Read the file
with open("src/mod_ui/services/effects_service/handlers.py", "r") as f:
    content = f.read()

# Pattern to find handler methods with old signature
pattern = r"async def (handle_\w+)\(self, request_data: Dict\[str, Any\]\) -> Dict\[str, Any\]:"
replacement = r"async def \1(self, request: ServiceRequest) -> Dict[str, Any]:"

# Fix handler signatures
content = re.sub(pattern, replacement, content)

# Pattern to fix request_data usage inside handlers
patterns_data = [
    (r"req = (\w+)\(\*\*request_data\)", r"req = \1(**request.data)"),
    (r"request_data\.get\(", r"request.data.get("),
    (r"instance = request_data\.get", r"instance = request.data.get"),
]

for old_pattern, new_pattern in patterns_data:
    content = re.sub(old_pattern, new_pattern, content)

# Write the fixed content back
with open("src/mod_ui/services/effects_service/handlers.py", "w") as f:
    f.write(content)

print("Fixed all handler signatures and request_data references")
