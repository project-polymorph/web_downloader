import yaml
import json
import tempfile
import subprocess
import os
from pathlib import Path
import multiprocessing
from functools import partial

def load_template(template_path):
    """Load the template file"""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_ai_classification(title, link, snippet, gen_struct_path, template):
    """Ask AI to classify if the content is related"""
    # Define the JSON schema for classification
    schema = {
        "type": "object",
        "properties": {
            "is_related": {
                "type": "string",
                "enum": ["True", "False", "NotSure"],
                "description": "Whether the content is related to transgender/LGBTQ+ topics"
            }
        },
        "required": ["is_related"],
        "additionalProperties": False
    }

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_input:
        # Fill in the template
        prompt = template.format(
            title=title or "Untitled",
            link=link,
            snippet=snippet or ""
        )
        temp_input.write(prompt)
        print(f"Prompt: {prompt}")
        temp_input_path = temp_input.name

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_schema:
        json.dump(schema, temp_schema)
        schema_file = temp_schema.name

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_output:
        temp_output_path = temp_output.name

    try:
        # Run gen_struct.py
        subprocess.run([
            'python', gen_struct_path,
            temp_input_path, temp_output_path, schema_file
        ], check=True)

        # Read the result
        with open(temp_output_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        print(f"Result: {result}")
        return result["is_related"].lower()  # Convert to lowercase to match YAML
    except Exception as e:
        print(f"Error during AI classification: {e}")
        return "unknown"
    finally:
        # Cleanup temporary files
        os.unlink(temp_input_path)
        os.unlink(temp_output_path)
        os.unlink(schema_file)

def process_url(template, gen_struct_path, url_data):
    """Process a single URL (to be run in parallel)"""
    url, data = url_data
    print(f"Processing: {url}")
    result = get_ai_classification(
        data.get('title'),
        url,
        data.get('snippet'),
        gen_struct_path,
        template
    )
    if result != 'unknown':
        return url, result
    return None

def main():
    # File paths
    links_path = Path('.github/links.yml')
    template_path = Path('.github/prompts/check_related.md.template')
    gen_struct_path = Path('.github/scripts/ai/gen_struct.py')

    # Load files
    with open(links_path, 'r', encoding='utf-8') as f:
        links_data = yaml.safe_load(f)

    template = load_template(template_path)

    # Process each unknown entry
    modified = False
    batch_count = 0
    
    # Get items needing processing
    to_process = [(url, data) for url, data in links_data.items() 
                 if not data.get('is_related') or data.get('is_related') == 'unknown']
    
    # Create a pool with 5 processes
    with multiprocessing.Pool(5) as pool:
        # Create a partial function with template and gen_struct_path
        process_func = partial(process_url, template, gen_struct_path)
        
        # Process items in chunks of 5
        for i in range(0, len(to_process), 5):
            chunk = to_process[i:i + 5]
            print(f"Processing batch {i//5 + 1}/{(len(to_process) + 4)//5}")
            
            # Process chunk in parallel
            results = pool.map(process_func, chunk)
            
            # Update results
            modified_in_batch = False
            for result in results:
                if result:
                    url, is_related = result
                    links_data[url]['is_related'] = is_related
                    modified = True
                    modified_in_batch = True
                    batch_count += 1
                    print(f"Updated {url} to {is_related}")
            
            # Write changes after every 6 batches
            if modified_in_batch and (i//5 + 1) % 6 == 0:
                with open(links_path, 'w', encoding='utf-8') as f:
                    yaml.dump(links_data, f, allow_unicode=True)
                    f.flush()
                    print(f"Batch of {batch_count} changes saved to links.yml")
                    batch_count = 0

    with open(links_path, 'w', encoding='utf-8') as f:
        yaml.dump(links_data, f, allow_unicode=True)
    if not modified:
        print("No changes were necessary")

if __name__ == "__main__":
    main()
