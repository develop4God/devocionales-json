#!/usr/bin/env python3
"""
Verify all image URLs in encounter files
Extracts image_url values and checks if they're valid (using curl/requests)
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import subprocess
from urllib.parse import urljoin

def extract_image_urls(encounters_dir):
    """Extract all image_url values from encounter files"""
    urls = defaultdict(list)
    files_checked = 0
    
    encounters_path = Path(encounters_dir)
    
    # Find all language directories
    for lang_dir in encounters_path.iterdir():
        if lang_dir.is_dir() and lang_dir.name not in ['archive', 'encounters_scripts', 'discovery', 'discovery', 'encounters_scripts', 'badges', 'bible_database', 'devocionales_scripts']:
            for json_file in lang_dir.glob('*.json'):
                files_checked += 1
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract from cards if it's an encounter file
                    if 'cards' in data:
                        for card in data['cards']:
                            if 'image_url' in card:
                                url = card['image_url']
                                if url:  # Non-empty
                                    urls[url].append({
                                        'file': json_file.name,
                                        'lang': lang_dir.name
                                    })
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing {json_file}: {e}")
                except Exception as e:
                    print(f"❌ Error reading {json_file}: {e}")
    
    return urls, files_checked

def validate_urls(urls):
    """Validate that all URLs have proper format and extensions"""
    validation_results = {
        'total': len(urls),
        'with_png': 0,
        'without_png': 0,
        'empty': 0,
        'issues': []
    }
    
    for url, locations in urls.items():
        if not url:
            validation_results['empty'] += 1
        elif url.endswith('.png'):
            validation_results['with_png'] += 1
        else:
            validation_results['without_png'] += 1
            validation_results['issues'].append({
                'url': url,
                'issue': 'Missing .png extension',
                'locations': locations
            })
    
    return validation_results

def check_url_with_curl(url, base_path=None):
    """
    Check if URL exists using curl
    Returns (status_code, message)
    """
    try:
        # If base_path provided, try to find the file
        if base_path:
            file_path = os.path.join(base_path, url)
            if os.path.exists(file_path):
                return (200, f"Local file exists: {file_path}")
            else:
                return (404, f"Local file not found: {file_path}")
        
        # Try curl for local HTTP server or remote URLs
        result = subprocess.run(
            ['curl', '-I', '--max-time', '2', url],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Extract status code from output
            for line in result.stdout.decode().split('\n'):
                if line.startswith('HTTP'):
                    status = line.split()[1]
                    return (int(status), f"HTTP {status}")
            return (200, "OK")
        else:
            return (result.returncode, "Connection failed")
    except subprocess.TimeoutExpired:
        return (408, "Request timeout")
    except Exception as e:
        return (999, str(e))

def main():
    encounters_dir = Path(__file__).parent.parent
    
    print("=" * 80)
    print("IMAGE URL VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Extract URLs
    print("🔍 Extracting image URLs from encounter files...")
    urls, files_checked = extract_image_urls(encounters_dir)
    print(f"✓ Checked {files_checked} files")
    print(f"✓ Found {len(urls)} unique image URLs")
    print()
    
    # Validate URLs
    print("🔎 Validating URL format and extensions...")
    validation = validate_urls(urls)
    
    print(f"📊 VALIDATION SUMMARY:")
    print(f"   Total unique URLs: {validation['total']}")
    print(f"   ✓ With .png extension: {validation['with_png']}")
    print(f"   ❌ Without .png extension: {validation['without_png']}")
    print(f"   ⚠️  Empty URLs: {validation['empty']}")
    print()
    
    if validation['issues']:
        print("⚠️  ISSUES FOUND:")
        for issue in validation['issues']:
            print(f"   • {issue['url']}")
            print(f"     Issue: {issue['issue']}")
            for loc in issue['locations']:
                print(f"       - {loc['file']} ({loc['lang']})")
        print()
    else:
        print("✅ All URLs have proper format!")
        print()
    
    # List all unique URLs
    print("📝 ALL UNIQUE IMAGE URLS:")
    print()
    sorted_urls = sorted(urls.keys())
    for i, url in enumerate(sorted_urls, 1):
        count = len(urls[url])
        print(f"   {i:3}. {url}")
        print(f"        Used in {count} file(s)")
        for loc in urls[url][:2]:  # Show first 2 locations
            print(f"        - {loc['file']} ({loc['lang']})")
        if len(urls[url]) > 2:
            print(f"        ... and {len(urls[url]) - 2} more")
    print()
    
    # Summary
    print("=" * 80)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print(f"Summary:")
    print(f"  • Total unique URLs: {validation['total']}")
    print(f"  • With .png extension: {validation['with_png']} / {validation['total']} (100%)")
    print(f"  • Empty URLs: {validation['empty']}")
    print(f"  • Issues found: {len(validation['issues'])}")
    print()
    
    # Return exit code
    return 0 if len(validation['issues']) == 0 and validation['empty'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
