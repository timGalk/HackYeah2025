import json
import re
import os

# Change to the correct directory
os.chdir(r'C:\Users\w1ndr\Documents\GitHub\HackYeah2025\Application')

# Read the reverse mapping file
with open('app/src/main/assets/node_name_mapping_reverse.json', 'r', encoding='utf-8') as f:
    reverse_mapping = json.load(f)

# Create the forward mapping (numeric ID -> Name)
forward_mapping = {}

for name, stop_id in reverse_mapping.items():
    # Extract numeric ID from stop_XXX_YYYYZZ format
    if isinstance(stop_id, str) and stop_id.startswith('stop_'):
        # Extract the numeric part (XXX from stop_XXX_YYYYZZ)
        match = re.match(r'stop_(\d+)_', stop_id)
        if match:
            numeric_id = match.group(1)
            forward_mapping[numeric_id] = name
    else:
        # It's already a numeric ID (just a number as string)
        forward_mapping[str(stop_id)] = name

# Sort by numeric ID for better readability
sorted_mapping = dict(sorted(forward_mapping.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999))

# Write the forward mapping file
with open('app/src/main/assets/node_name_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)

print(f"✓ Created node_name_mapping.json with {len(forward_mapping)} entries")
print("\nSample entries:")
for i, (k, v) in enumerate(list(sorted_mapping.items())[:10]):
    print(f'  "{k}": "{v}"')
print("\nMapping complete!")

