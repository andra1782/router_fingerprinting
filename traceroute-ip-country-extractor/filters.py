import argparse
import os

parser = argparse.ArgumentParser(description="Filter IPs by country, city, ASN, or organization.")
parser.add_argument("input_file", help="File with IPs and metadata (CSV format: ip,country,city,asn,organization).")

parser.add_argument("--country", help="Country name to filter by (default filter).")
parser.add_argument("--city", help="City name to filter by.")
parser.add_argument("--asn", help="ASN to filter by.")
parser.add_argument("--org", help="Organization name to filter by.")

parser.add_argument("--output_file", help="Optional output file to save matching IPs.", default=None)

args = parser.parse_args()

matched_ips = []

with open(args.input_file, "r", encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",", 4)
        if len(parts) < 5:
            continue

        ip, country, city, asn, org = [p.strip().lower() for p in parts]

        if args.country and country != args.country.strip().lower():
            continue
        if args.city and city != args.city.strip().lower():
            continue
        if args.asn and asn != args.asn.strip().lower():
            continue
        if args.org and org != args.org.strip().lower():
            continue

        matched_ips.append(parts[0])  

if not args.output_file:
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    filters = []
    if args.country: filters.append(f"country_{args.country.replace(' ', '_')}")
    if args.city: filters.append(f"city_{args.city.replace(' ', '_')}")
    if args.asn: filters.append(f"asn_{args.asn}")
    if args.org: filters.append(f"org_{args.org.replace(' ', '_')}")
    suffix = "_".join(filters) if filters else "country_default"
    args.output_file = f"{base_name}_filtered_{suffix}.txt"

with open(args.output_file, "w", encoding='utf-8') as out:
    for ip in matched_ips:
        out.write(ip + "\n")

print(f"Found {len(matched_ips)} IPs matching filters. Saved to {args.output_file}.")
