#!/usr/bin/env python3
"""
Fix effects router make_request calls to use correct parameter order
"""
import re

# Read the file
with open("src/mod_ui/services/webui_gateway/routers/effects.py", "r") as f:
    content = f.read()

# Pattern to find make_request calls with wrong parameter order
# Looking for: make_request("effects_service", "effect_xxx", data)
# Should be: make_request("effect_xxx", data, "effects_service")
pattern = r'make_request\(\s*"effects_service",\s*"([^"]+)",\s*([^)]+)\)'
replacement = r'make_request(\n            "\1",\n            \2,\n            "effects_service"\n        )'

# Replace all occurrences
fixed_content = re.sub(pattern, replacement, content)

# Write the fixed content back
with open("src/mod_ui/services/webui_gateway/routers/effects.py", "w") as f:
    f.write(fixed_content)

print("Fixed effects router make_request calls")
