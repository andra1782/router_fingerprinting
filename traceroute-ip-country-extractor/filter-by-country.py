import argparse
import os

parser = argparse.ArgumentParser(description="Filter IPs by country.")
parser.add_argument("input_file", help="File with IPs and countries (CSV format).")
parser.add_argument("country", nargs="+", help="Country name to filter by.")
parser.add_argument("--output_file", help="Optional output file to save matching IPs.", default=None)

args = parser.parse_args()
country_filter = " ".join(args.country).lower().strip()

matched_ips = []

with open(args.input_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            ip, country = line.split(",", 1)
            if country.strip().lower() == country_filter:
                matched_ips.append(ip.strip())
        except ValueError:
            continue

if not args.output_file:
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    formatted_country = " ".join(args.country).replace(" ", "_")
    args.output_file = f"{base_name}_ips_{formatted_country}.txt"

with open(args.output_file, "w") as out:
    for ip in matched_ips:
        out.write(ip + "\n")

print(f"Found {len(matched_ips)} IPs from {args.country}. Saved to {args.output_file}.")
