import json
import re

# Read the reverse mapping file
with open('app/src/main/assets/node_name_mapping_reverse.json', 'r', encoding='utf-8') as f:
    reverse_mapping = json.load(f)

# Create the forward mapping (ID -> Name)
forward_mapping = {}

for name, stop_id in reverse_mapping.items():
    # Extract numeric ID from stop_XXX_YYYYZZ format
    # Or use the ID directly if it's already numeric
    if stop_id.startswith('stop_'):
        # Extract the numeric part (XXX from stop_XXX_YYYYZZ)
        match = re.match(r'stop_(\d+)_', stop_id)
        if match:
            numeric_id = match.group(1)
            forward_mapping[numeric_id] = name
    else:
        # It's already a numeric ID
        forward_mapping[stop_id] = name

# Write the forward mapping file
with open('app/src/main/assets/node_name_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(forward_mapping, f, ensure_ascii=False, indent=2)

print(f"Created node_name_mapping.json with {len(forward_mapping)} entries")
print("Sample entries:")
for i, (k, v) in enumerate(list(forward_mapping.items())[:5]):
    print(f"  \"{k}\": \"{v}\"")

