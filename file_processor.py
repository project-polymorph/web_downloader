import os
import shutil
import argparse
import yaml
from pathlib import Path

def is_valid_cleaned_file(file_path):
    """Check if a file is valid by reading its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check if file is not empty and doesn't contain error messages
            if content.strip() and content.strip() not in ['太长', '爬取错误']:
                return True
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return False

def get_original_links(page_yml_path):
    """Get original links from page.yml."""
    try:
        with open(page_yml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading page.yml: {e}")
        return {}

def append_original_link(file_path, original_link):
    """Append original link as a comment to the end of the file."""
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"\n<!-- tcd_original_link {original_link} -->\n")
    except Exception as e:
        print(f"Error appending original link to {file_path}: {e}")

def process_files(source_dir, target_dir):
    """Process and copy valid files from source to target directory."""
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    # mkdir target_dir if not exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Process ready directory
    ready_dir = source_dir / 'ready'
    if not ready_dir.exists():
        print(f"Ready directory not found: {ready_dir}")
        return
    
    # Get original links from page.yml
    downloads_dir = source_dir / 'downloads'
    page_yml = downloads_dir / 'page.yml'
    original_links = get_original_links(page_yml)
    
    # Copy valid files from ready directory
    for file_path in ready_dir.glob('*.md'):
        if is_valid_cleaned_file(file_path):
            target_file = target_dir / file_path.name
            try:
                shutil.copy2(file_path, target_file)
                print(f"Copied: {file_path.name}")
                # Append original link to the copied file
                file_name_html = file_path.name.replace('.md', '.html')
                if file_name_html in original_links:
                    original_link = original_links[file_name_html]['link']
                    append_original_link(target_file, original_link)
                else:
                    print("not found" + file_name_html)
            except Exception as e:
                print(f"Error copying {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Process and copy cleaned files')
    parser.add_argument('source_dir', help='Source directory path')
    parser.add_argument('target_dir', help='Target directory path')
    
    args = parser.parse_args()
    
    process_files(args.source_dir, args.target_dir)

if __name__ == '__main__':
    main()