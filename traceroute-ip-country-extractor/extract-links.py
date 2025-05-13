import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

parser = argparse.ArgumentParser(description="Extract links from daily dump index")
parser.add_argument("url", help="Daily dump index URL")
args = parser.parse_args()

response = requests.get(args.url)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
links = soup.find_all("a")

output_file = "archive_links.txt"

with open(output_file, "w") as f:
    for link in links:
        href = link.get("href", "")
        if "traceroute" in href and href.endswith(".bz2"):
            full_url = urljoin(args.url, href)
            f.write(full_url + "\n")

print(f"Output printed to {output_file}");
