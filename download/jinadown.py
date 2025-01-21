import os
import hashlib
import subprocess
from pathlib import Path
import json
import time
def get_file_md5(filepath):
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def download_jina(url, output_dir, title):
    """Download webpage content using Jina Reader API"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate safe base filename from title
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        base_name = safe_title.replace(' ', '_')[:100]
        filename = f"{base_name}.md"
        output_path = os.path.join(output_dir, filename)
        # sleep 10 seconds to avoid rate limit
        time.sleep(10)
        # Prepare curl command with Jina Reader headers
        jina_url = f"https://r.jina.ai/{url}"
        command = [
            'curl',
            '--location',
            jina_url,
            '-H', 'X-With-Iframe: true',
            '-H', 'X-With-Shadow-Dom: true',
            '-H', 'X-With-Images-Summary: true',
            '--no-progress-meter',
            '-v'
        ]
        
        # Execute curl command
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"curl failed with error: {result.stderr}")
        
        # Save the content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        return True, output_path
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False, str(e) 