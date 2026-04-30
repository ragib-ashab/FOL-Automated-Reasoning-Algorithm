import os
import urllib.request
import re
import html

DOMAIN = "SYN"
INDEX_URL = f"https://tptp.org/cgi-bin/SeeTPTP?Category=Problems&Domain={DOMAIN}"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(CURRENT_DIR, "dataset", "SYN")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
print(f"Fetching index for {DOMAIN}...")

try:
    with urllib.request.urlopen(INDEX_URL) as response:
        index_html = response.read().decode('utf-8')

    files_to_download = list(set(re.findall(rf'File=({DOMAIN}[a-zA-Z0-9\-\+]+\.p)', index_html)))
    print(f"Found {len(files_to_download)} files. Starting download...")

    for filename in files_to_download:
        file_url = f"https://tptp.org/cgi-bin/SeeTPTP?Category=Problems&Domain={DOMAIN}&File={filename}"
        
        with urllib.request.urlopen(file_url) as response:
            raw_content = response.read().decode('utf-8')
            
        clean_text = re.sub(r'<[^>]+>', '', raw_content) 
        clean_text = html.unescape(clean_text)           
        
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        with open(filepath, 'w') as f:
            f.write(clean_text.strip())
            
        print(f"Downloaded: {filename}")

    print("\nBatch download complete!")
    
except Exception as e:
    print(f"An error occurred: {e}")