import argparse
import os

parser = argparse.ArgumentParser(description="Filter IPs by country, city, ASN, or organization.")
parser.add_argument("input_file", help="File with IPs and metadata (CSV format: ip,country,city,asn,organization).")

parser.add_argument("--country", nargs="*", help="Country name(s) to filter by (zero or more).")
parser.add_argument("--city", nargs="*", help="City name(s) to filter by (zero or more).")
parser.add_argument("--asn", nargs="*", help="ASN(s) to filter by (zero or more).")
parser.add_argument("--org", nargs="*", help="Organization name(s) to filter by (zero or more).")

parser.add_argument("--verbose", action="store_true", help="Outputs extra information for the filtered IPs.")
parser.add_argument("--output_file", help="Optional output file to save matching IPs.", default=None)

args = parser.parse_args()

def normalize_list(lst):
    return [x.strip().lower() for x in lst] if lst else []

countries = normalize_list(args.country)
cities = normalize_list(args.city)
asns = normalize_list(args.asn)
orgs = normalize_list(args.org)

def match_any(value, filters):
    return not filters or value in filters

matched = []


with open(args.input_file, "r", encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",", 4)
        if len(parts) < 5:
            continue

        ip, country, city, asn, org = [p.strip().lower() for p in parts]

        if not match_any(country, countries): continue
        if not match_any(city, cities): continue
        if not match_any(asn, asns): continue
        if not match_any(org, orgs): continue

        matched.append(line if args.verbose else ip)

if not args.output_file:
    base_name = os.path.splitext(os.path.basename(args.input_file.replace(" ", "_")))[0]
    filters = []

    if countries: filters.append("country_" + "_".join(c.replace(" ", "_") for c in countries))
    if cities: filters.append("city_" + "_".join(c.replace(" ", "_") for c in cities))
    if asns: filters.append("asn_" + "_".join(asns))
    if orgs: filters.append("org_" + "_".join(o.replace(" ", "_") for o in orgs))

    suffix = "_".join(filters) if filters else "all"
    args.output_file = f"{base_name}_filtered_{suffix}.txt"

with open(args.output_file, "w", encoding='utf-8') as out:
    for item in matched:
        out.write(item + "\n")

print(f"Found {len(matched)} IPs matching filters. Saved to {args.output_file}.")
