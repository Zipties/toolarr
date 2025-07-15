import re

with open('main.py', 'r') as f:
    content = f.read()

# For Pydantic models, change Optional fields to have defaults instead of None
# This avoids the anyOf schema issue
replacements = [
    # In models, use Field with default
    (r'(\s+)seriesId: Optional\[int\] = None', r'\1seriesId: int = Field(0, description="Series ID (0 for none)")'),
    (r'(\s+)episodeIds: Optional\[List\[int\]\] = None', r'\1episodeIds: List[int] = Field(default_factory=list, description="Episode IDs")'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open('main.py', 'w') as f:
    f.write(content)

print("Fixed Optional fields in models")
