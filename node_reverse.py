import json

with open("node_name_mapping_reverse.json", "r") as f:
    data = json.load(f)

new_data = {value: key for key, value in data.items()}

with open("node_name_mapping_reduced.json", "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=4)