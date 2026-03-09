#!/usr/bin/env python3
"""Fix compound creation loop to elevate third compound in Airport mission."""

import re

# Read the file
with open('src/choplifter/mission_state.py', 'r') as f:
    content = f.read()

# Find and replace the compound creation loop
old_pattern = r'        for x in level\.compound_xs:\n            compounds\.append\(\n                Compound\(\n                    pos=Vec2\(x, compound_y\),'

new_code = '''        for i, x in enumerate(level.compound_xs):
            # Airport mission: float third compound 30px up to match meal truck box height
            y_offset = -30.0 if mission_id.lower() in ("airport", "airport_special_ops") and i == 2 else 0.0
            compounds.append(
                Compound(
                    pos=Vec2(x, compound_y + y_offset),'''

content = re.sub(old_pattern, new_code, content, count=1)

# Write the file
with open('src/choplifter/mission_state.py', 'w') as f:
    f.write(content)

print("✓ Compound creation loop updated successfully")
