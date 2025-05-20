import geoip2.database
import argparse
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent
DB_DIR = PROJ_DIR / "databases"

def get_country(ip, reader):
    try:
        response = reader.country(ip)
        return response.country.name
    except geoip2.errors.AddressNotFoundError:
        return None

def get_city(ip, reader):
    try:
        response = reader.city(ip)
        return response.city.name
    except geoip2.errors.AddressNotFoundError:
        return None
    
def get_asn(ip, reader):
    try:
        response = reader.asn(ip)
        return response.autonomous_system_number, response.autonomous_system_organization
    except geoip2.errors.AddressNotFoundError:
        return None, None
    
parser = argparse.ArgumentParser(description="Find the country, city, ASN and organization of each IP within a text file")
parser.add_argument("ip_file", help="File with list of IPs (both IPv4 and IPv6)")
parser.add_argument("--output_file", help="Output file of format {IP, Country, City, ASN, Organization}")
parser.add_argument("geoip_country_db", help="Name of the MaxMind GeoIP2 country database file in the databases folder")
parser.add_argument("geoip_city_db", help="Name of the MaxMind GeoIP2 city database file in the databases folder")
parser.add_argument("geoip_asn_db", help="Name of the MaxMind GeoIP2 ASN database file in the databases folder")

args = parser.parse_args()

ip_file_path = Path(args.ip_file).resolve()  
geoip_country_db_path = DB_DIR / args.geoip_country_db
geoip_city_db_path = DB_DIR / args.geoip_city_db
geoip_asn_db_path = DB_DIR / args.geoip_asn_db

# Check if database files exist
if not geoip_country_db_path.exists():
    print(f"Error: Country database file not found: {geoip_country_db_path}")
    exit(1)
if not geoip_city_db_path.exists():
    print(f"Error: City database file not found: {geoip_city_db_path}")
    exit(1)
if not geoip_asn_db_path.exists():
    print(f"Error: ASN database file not found: {geoip_asn_db_path}")
    exit(1)

if not args.output_file:
    base_name = ip_file_path.stem
    args.output_file = ip_file_path.parent / f"{base_name}.txt"

output_file_path = Path(args.output_file).resolve()  
output_file_path.parent.mkdir(parents=True, exist_ok=True)

lines_processed = 0

with geoip2.database.Reader(geoip_country_db_path) as reader_country, \
     geoip2.database.Reader(geoip_city_db_path) as reader_city, \
     geoip2.database.Reader(geoip_asn_db_path) as reader_asn:
    with ip_file_path.open("r", encoding='utf-8') as ip_file, \
         output_file_path.open("w", encoding='utf-8') as output_file:
        for line in ip_file:
            ip = line.strip()
            country = get_country(ip, reader_country)
            city = get_city(ip, reader_city)
            asn, org = get_asn(ip, reader_asn)

            country_out = country if country else "Unknown"
            city_out = city if city else "Unknown"
            asn_out = asn if asn else "Unknown"
            org_out = org if org else "Unknown"

            output_file.write(f"{ip},{country_out},{city_out},{asn_out},{org_out}\n")
            lines_processed += 1

            if lines_processed % 5000 == 0:
                print(f"\rProcessed {lines_processed} lines...", end="", flush=True)

print(f"\rProcessed {lines_processed} lines.", end="", flush=True)
print(f"\nFinished processing. Results saved to {output_file_path}.")
