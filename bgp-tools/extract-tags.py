#!/usr/bin/env python3
import os
import argparse
import requests
from pathlib import Path

BASE_URL = "https://bgp.tools/tags/{}.csv"
TAGS_TXT_URL = "https://bgp.tools/tags.txt"
SCRIPT_DIR = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(
        description="Download tag CSVs from bgp.tools"
    )
parser.add_argument("-o", "--output-dir", default="csvs", help="default: 'csvs' (under script location)")

def fetch_tags_info():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(TAGS_TXT_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"Failed to download tags.txt: {e}")
        return None

def download_tags(tags_txt):
    tags = []
    for line in tags_txt.strip().splitlines():
        if not line.strip():
            continue
        tag = line.split(",", 1)[0].strip()
        if tag:
            tags.append(tag)
    return tags

def download_csv(tag, output_dir):
    url = BASE_URL.format(tag)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 dont "
            "AppleWebKit/537.36 block "
            "Chrome/114.0.0.0 meh "
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to download '{tag}.csv': {e}")
        return False

    out_path = output_dir / f"{tag}.csv"
    with open(out_path, "wb") as fout:
        fout.write(resp.content)
    print(f"Downloaded '{tag}.csv'")
    return True

def main():
    args = parser.parse_args()
    output_dir = (SCRIPT_DIR / args.output_dir).resolve()
    os.makedirs(output_dir, exist_ok=True)

    tags_txt = fetch_tags_info()
    if not tags_txt:
        print("FAILED TO FETCH TAGS.TXT")
        return

    tags = download_tags(tags_txt)
    print(f"Downloading {len(tags)} tags into '{output_dir}'...")

    success = 0
    for tag in tags:
        if download_csv(tag, output_dir):
            success += 1

    print(f"\nDone. {success}/{len(tags)} files downloaded successfully")

if __name__ == "__main__":
    main()
