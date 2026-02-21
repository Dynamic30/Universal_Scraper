import subprocess
import os
from urllib.parse import urlparse


def lighthouse(url,base_dir):
    domain = urlparse(url).hostname or "unknown"
    dir = os.path.join(base_dir,"Light_House",domain)
    subprocess.run([
        "lighthouse",
        url,
        "--output=json",
        "--output=html",
        f"--output-path={dir}",
        "--quiet",
        "--chrome-flags=--headless"
    ])

lighthouse()