#!/usr/bin/env python3
"""
Fix session_request calls in the session router
"""
import re


def fix_session_request_calls(file_path):
    with open(file_path, "r") as f:
        content = f.read()

    # Pattern to match session_request calls with old parameters
    old_pattern = r'await session_request\(\s*service="session",\s*endpoint="([^"]+)",\s*method="([^"]+)"(?:,\s*data=([^)]+))?\s*\)'

    def replacement(match):
        endpoint = match.group(1)
        method = match.group(2)
        data = match.group(3) if match.group(3) else None

        if data:
            return f'await session_request("{endpoint}", "{method}", {data})'
        else:
            return f'await session_request("{endpoint}", "{method}")'

    # Replace the patterns
    new_content = re.sub(old_pattern, replacement, content)

    # Write back the fixed content
    with open(file_path, "w") as f:
        f.write(new_content)

    print(f"Fixed session_request calls in {file_path}")


if __name__ == "__main__":
    fix_session_request_calls(
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/webui_gateway/routers/session.py"
    )
