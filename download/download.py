from datetime import datetime
import random
import time
import yaml
import os
import argparse
from pathlib import Path
import json
from pdfdown import download_pdf, get_file_md5
from webdown import download_webpage
import hashlib
import re

def check_file_exists_by_md5(md5_hash):
    """Check if file exists in visit_links.yml"""
    try:
        with open('.github/visit_links.yml', 'r', encoding='utf-8') as f:
            visited_data = yaml.safe_load(f) or {}
            return md5_hash in visited_data
    except FileNotFoundError:
        return False

def update_visit_links(url, info, md5, output_path):
    """Update visit_links.yml with new download information"""
    try:
        # Read existing data
        visit_links_path = '.github/visit_links.yml'
        try:
            with open(visit_links_path, 'r', encoding='utf-8') as f:
                visited_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            visited_data = {}

        # Add new entry
        visited_data[md5] = {
            'snippet': info.get('snippet', ''),
            'title': info.get('title', ''),
            'link': url,
            'visited_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save updated data
        with open(visit_links_path, 'w', encoding='utf-8') as f:
            yaml.dump(visited_data, f, allow_unicode=True)
        
        print("✓ Updated visit_links.yml")
        return True
    except Exception as e:
        print(f"✗ Error updating visit_links.yml: {e}")
        return False

def check_link_exists(url, visited_data):
    """Check if a URL has already been processed"""
    for entry in visited_data.values():
        if entry.get('link') == url:
            return True
    return False

def process_links_file(yaml_path, output_dir, related_filter='true', file_pattern=r'.*pdf.*', download_type='both', sleep_duration=30, download_order='sequential'):
    """Process YAML file and download files based on is_related filter and file pattern"""
    print("\n" + "="*50)
    print(f"Starting download process:")
    print(f"  YAML file: {yaml_path}")
    print(f"  Output directory: {output_dir}")
    print(f"  Filter: is_related='{related_filter}'")
    print(f"  File pattern: {file_pattern}")
    print(f"  Download type: {download_type}")
    print(f"  Download order: {download_order}")
    print("="*50 + "\n")
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Read YAML file
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        print(f"✓ Successfully loaded YAML file with {len(data)} entries")
    except Exception as e:
        print(f"✗ Error loading YAML file: {e}")    
    # Track results
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    # Create results.json path
    results_file = os.path.join(output_dir, 'results.json')
    
    # Load visit_links.yml at the start
    try:
        with open('.github/visit_links.yml', 'r', encoding='utf-8') as f:
            visited_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        visited_data = {}
    
    # Initialize seen_md5s from visit_links.yml
    seen_md5s = set(visited_data.keys())
    
    # Convert data items to list and randomize if needed
    data_items = list(data.items())
    if download_order == 'random':
        random.shuffle(data_items)
    
    # Process each entry (modified to use data_items instead of data.items())
    total = len(data_items)
    for idx, (url, info) in enumerate(data_items, 1):
        print(f"\nProcessing entry {idx}/{total}:")
        print(f"URL: {url}")
        print(f"is_related: '{info.get('is_related', 'unknown')}'")
        
        # Check if link already exists in visit_links.yml
        if check_link_exists(url, visited_data):
            print("→ Skipping: Link already processed")
            results['skipped'].append((url, "Link already processed"))
            continue
        
        # Skip if is_related doesn't match filter
        if related_filter != 'all' and info.get('is_related', '').lower() != related_filter.lower():
            print("→ Skipping: is_related value doesn't match filter")
            results['skipped'].append((url, f"is_related='{info.get('is_related', '')}'"))
            continue
        
        # Filter files based on regex pattern
        if not re.search(file_pattern, url, re.IGNORECASE):
            print(f"→ Skipping: Path does not match pattern '{file_pattern}'")
            results['skipped'].append((url, f"Path does not match pattern '{file_pattern}'"))
            continue
    
        if not url:
            print("✗ Error: No download link provided")
            results['failed'].append((url, "No link provided"))
            continue
        
        print(f"→ Downloading from: {url}")

        # add random sleep with configured duration
        sleep_time = random.randint(sleep_duration // 2, sleep_duration)
        time.sleep(sleep_time)
        
        # Download file
        try:
            title = info.get('title', '')
            if not title or title == '' or title == 'Untitled':
                title = info['snippet'][10:30]
            
            # Choose download function based on download_type
            if download_type == 'pdf':
                success, result = download_pdf(url, output_dir, title)
            elif download_type == 'webpage':
                success, result = download_webpage(url, output_dir, title)
            else:
                print(f"✗ Invalid download type: {download_type}")
                continue
            
            if success:
                output_path = result  # result contains the file path on success
                # Calculate MD5 and update visit_links.yml
                md5 = get_file_md5(output_path)
                if update_visit_links(url, info, md5, output_path):
                    results['success'].append({
                        'url': url,
                        'path': output_path,
                        'md5': md5,
                        'title': info.get('title', ''),
                        'snippet': info.get('snippet', '')
                    })
                    print(f"✓ Successfully downloaded ({os.path.getsize(output_path)} bytes)")
                    print(f"  MD5: {md5}")
                    
                    # Move MD5 duplicate check here, inside the success block
                    file_md5 = calculate_md5(output_path)
                    if file_md5 in seen_md5s:
                        print(f"→ Duplicate MD5 detected: {file_md5}")
                        # Mark as not related since it's a duplicate
                        data[url]['is_related'] = 'duplicate'
                        # Save the changes back to the YAML file
                        with open(yaml_path, 'w', encoding='utf-8') as f:
                            yaml.dump(data, f, allow_unicode=True)
                        print("→ Marked as not related due to duplicate content")
                        # remove the file
                        os.remove(output_path)
                        print(f"  Removed duplicate file: {output_path}")
                    else:
                        seen_md5s.add(file_md5)
                else:
                    results['failed'].append({
                        'url': url,
                        'error': "Failed to update visit_links.yml",
                        'title': info.get('title', ''),
                        'snippet': info.get('snippet', '')
                    })
            else:
                results['failed'].append({
                    'url': url,
                    'error': result,
                    'title': info.get('title', ''),
                    'snippet': info.get('snippet', '')
                })
                print(f"✗ Download failed: {result}")
        except Exception as e:
            results['failed'].append({
                'url': url,
                'error': str(e),
                'title': info.get('title', ''),
                'snippet': info.get('snippet', '')
            })
            print(f"✗ Unexpected error: {e}")
            continue

        # Save results.json after each file
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': results['success'],
                    'failed': results['failed'],
                    'skipped': results['skipped']
                }, f, indent=2)
            print("✓ Updated results.json")
        except Exception as e:
            print(f"Error updating results.json: {e}")
            continue

def calculate_md5(filepath):
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def main():
    parser = argparse.ArgumentParser(
        description='Download files from URLs listed in a YAML file.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--related',
        choices=['true', 'false', 'notsure', 'all'],
        default='true',
        help='Filter entries by is_related value'
    )
    
    parser.add_argument(
        '--pattern',
        default=r'.*pdf.*',
        help='Regex pattern to filter file URLs (case-insensitive, default: .*pdf.*)'
    )

    parser.add_argument(
        '--download-type',
        choices=['pdf', 'webpage', 'both'],
        default='pdf',
        help='Type of download to perform (default: both)'
    )

    parser.add_argument(
        '--yaml-path',
        default='.github/links.yml',
        help='Path to the YAML file containing links'
    )

    parser.add_argument(
        '--output-dir',
        default='workspace',
        help='Directory where downloaded files will be saved'
    )

    parser.add_argument(
        '--sleep',
        type=int,
        default=30,
        help='Maximum sleep duration between downloads in seconds (default: 30)'
    )

    parser.add_argument(
        '--order',
        choices=['sequential', 'random'],
        default='sequential',
        help='Order of processing downloads (sequential or random)'
    )

    args = parser.parse_args()
    
    print("\nStarting download script with settings:")
    print(f"  YAML path: {args.yaml_path}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Related filter: {args.related}")
    print(f"  File pattern: {args.pattern}")
    print(f"  Download type: {args.download_type}")
    print(f"  Sleep duration: {args.sleep}s")
    print(f"  Download order: {args.order}")

    # Process the files
    results = process_links_file(
        args.yaml_path, 
        args.output_dir, 
        args.related, 
        args.pattern, 
        args.download_type,
        args.sleep,
        args.order
    )

    # Return non-zero exit code if there were any failures
    return 0

if __name__ == "__main__":
    exit(main())
