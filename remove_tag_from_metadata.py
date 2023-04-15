import os
import json
import re
import exiftool
from tqdm import tqdm

source_directory = 'path/to/your/images'  # Replace with the path to your source directory

def process_file(file_path):
    updates = []
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(file_path)
        for tag, value in metadata.items():
            # Remove 'People' if it's not followed by '/' or '|'
            new_value = re.sub(r'\bPeople\b(?!\/|\|)', ' ', str(value))
            if value != new_value:
                et.execute(b'-overwrite_original', f'-{tag}={new_value}'.encode('utf-8'), file_path.encode('utf-8'))
                updates.append({
                    'tag': tag,
                    'unmodified': value,
                    'modified': new_value
                })
    return updates

def get_image_files(source_directory):
    for root, _, files in os.walk(source_directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.tiff', '.png', '.gif', '.bmp')):
                yield os.path.join(root, file)

# Count the total number of image files
total_files = sum(1 for _ in get_image_files(source_directory))

output = []

# Traverse the directory and subdirectories
for file_path in tqdm(get_image_files(source_directory), total=total_files, desc="Processing images"):
    # Process the image and check if it was updated
    updates = process_file(file_path)
    if updates:
        output.append({
            'filepath': file_path,
            'updates': updates
        })

# Write the output to a JSON file
with open('removed.json', 'w') as outfile:
    json.dump(output, outfile, indent=4)

print("Done.")
