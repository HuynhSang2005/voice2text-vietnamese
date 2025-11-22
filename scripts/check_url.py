import urllib.request
import urllib.error

url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-2025-04-20.tar.bz2"

try:
    print(f"Checking {url}...")
    with urllib.request.urlopen(url) as response:
        print(f"Status: {response.status}")
        print("URL exists!")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
