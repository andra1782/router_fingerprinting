import subprocess
import argparse
import requests
import bz2
import shutil
import sys
import datetime
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJ_DIR / "data"
DB_DIR = PROJ_DIR / "databases"

def check_and_create_dir(path):
    path.mkdir(parents=True, exist_ok=True)

def prepare_dirs(run_dir, filter_dir_name):
    filter_dir = run_dir / "filtered_ips" / filter_dir_name
    check_and_create_dir(filter_dir)
    check_and_create_dir(DATA_DIR)
    check_and_create_dir(run_dir)
    check_and_create_dir(run_dir / "results")
    check_and_create_dir(run_dir / "filtered_ips")
    check_and_create_dir(run_dir / "archives")
    check_and_create_dir(run_dir / "extracted")
    check_and_create_dir(run_dir / "ips")
    check_and_create_dir(run_dir / "ips_plus_details")

def download_file(url, dest_path): 
    if dest_path.exists():
        print(f"File {dest_path} already exists. Skipping download.")
        return

    print(f"Starting download: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    chunk_size = 1024 * 1024

    if not url.endswith('.bz2'):
        print("Error: URL doesn't end with .bz2.")
        return

    with dest_path.open('wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size:
                    done = int(50 * downloaded / total_size)
                    sys.stdout.write(f"\r    [{'=' * done}{' ' * (50 - done)}] {100 * downloaded // total_size}%")
                    sys.stdout.flush()
    print(f"\nDownload completed: {dest_path}")

def extract_bz2(bz2_path, extract_path):
    if extract_path.exists():
        print(f"File {extract_path} already exists. Skipping extraction")
        return
    
    print(f"Extracting {bz2_path} to {extract_path}")
    with bz2.BZ2File(bz2_path, 'rb') as f_in:
        with open(extract_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024*1024)
    print("Extraction complete")

def run_script(script_name, args):
    print(f"Running script: {script_name} {' '.join(args)}")
    subprocess.run(["python", script_name] + args, check=True)
    print(f"Finished script: {script_name}")


def extract_ips(archive_url, run_dir, skip_extraction=False):
    archive_name = Path(archive_url).name
    archive_path = run_dir / "archives" / archive_name
    extract_path = run_dir / "extracted" / archive_name[:-4]  

    try:
        if not skip_extraction:
            download_file(archive_url, archive_path)
            extract_bz2(archive_path, extract_path)

            base_name = extract_path.name
            ip_file = run_dir / "ips" / f"{base_name}_ips.txt"
            
            if args.multithreading:
                run_script("extract-ips.py", [str(extract_path), "--output_file", str(ip_file), "--multithreading", str(args.multithreading)])
            else:
                run_script("extract-ips.py", [str(extract_path), "--output_file", str(ip_file)])
        else:
            base_name = extract_path.name
            ip_file = run_dir / "ips" / f"{base_name}_ips.txt"
            if not ip_file.exists():
                print(f"Error: IP file not found: {ip_file}")
                print("Make sure to run the full pipeline first or provide the correct IP file.")
                return
    finally:
        if not skip_extraction and not args.keep_temp:
            if archive_path.exists():
                archive_path.unlink()
                print(f"Deleted archive: {archive_path}")
            if extract_path.exists():
                extract_path.unlink()
                print(f"Deleted extracted file: {extract_path}")

def process(archive_url, run_dir, filter_dir_name, geoip_country_db_path, geoip_city_db_path, geoip_asn_db_path, countries=[], cities=[], asns=[], orgs=[], skip_extraction=False, fast=False):
    archive_name = Path(archive_url).name
    archive_path = run_dir / "archives" / archive_name
    extract_path = run_dir / "extracted" / archive_name[:-4]  

    try:
        if not skip_extraction:
            download_file(archive_url, archive_path)
            extract_bz2(archive_path, extract_path)

            base_name = extract_path.name
            ip_file = run_dir / "ips" / f"{base_name}_ips.txt"
            
            if args.multithreading:
                run_script("extract-ips.py", [str(extract_path), "--output_file", str(ip_file), "--multithreading", str(args.multithreading)])
            else:
                run_script("extract-ips.py", [str(extract_path), "--output_file", str(ip_file)])
        else:
            base_name = extract_path.name
            ip_file = run_dir / "ips" / f"{base_name}_ips.txt"
            if not ip_file.exists():
                print(f"Error: IP file not found: {ip_file}")
                print("Make sure to run the full pipeline first or provide the correct IP file.")
                return

        details_file = run_dir / "ips_plus_details" / f"{base_name}_ips.txt"
        
        filter_dir = run_dir / "filtered_ips" / filter_dir_name
            
        filtered_file = filter_dir / f"{base_name}_ips.txt"
        
        filter_args = [str(details_file), "--output_file", str(filtered_file)]

        if countries:
            filter_args.extend(["--country"] + countries)
        if cities:
            filter_args.extend(["--city"] + cities)
        if asns:
            filter_args.extend(["--asn"] + asns)
        if orgs:
            filter_args.extend(["--org"] + orgs)
        if args.verbose:
            filter_args.append("--verbose")

        run_script("extract-details.py", [str(ip_file), "--output_file", str(details_file), geoip_country_db_path, geoip_city_db_path, geoip_asn_db_path])
        run_script("filters.py", filter_args)

    finally:
        if not skip_extraction and not args.keep_temp:
            if archive_path.exists():
                archive_path.unlink()
                print(f"Deleted archive: {archive_path}")
            if extract_path.exists():
                extract_path.unlink()
                print(f"Deleted extracted file: {extract_path}")

    print(f"Done processing: {archive_name}")
    print("-" * 60)
    

def combine_ips_in_dir(dir_name):
    if dir_name.exists():
        print(f"Processing {dir_name}")

        ips = set()

        for file_path in dir_name.iterdir():
            if file_path.is_file() and file_path.suffix == ".txt":
                print(f"  Reading {file_path.name}")
                with file_path.open("r", encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            ips.add(line)
        return ips
            

def combine_ips(run_dir, filter_dir_name):
    # Combine IPs only from the specified filter directory
    filter_dir = run_dir / "filtered_ips" / filter_dir_name
    if filter_dir.exists():
        print(f"Processing {filter_dir_name}")
        ips = combine_ips_in_dir(filter_dir)
        
        # Create results file with matching name
        results_file = run_dir / "results" / f"{filter_dir_name}_results.txt"
        with results_file.open("w", encoding='utf-8') as out:
            for ip in sorted(ips):
                out.write(ip + "\n")
        
        print(f"Wrote {len(ips)} unique IPs to {results_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .bz2 traceroutes from online resources, extract their IPs and filter them by country.")
    parser.add_argument("--url_file", help="Text file with list of archive URLs (one per line)")
    parser.add_argument("--url",  help="Atlas Daily Dump Index URL (specific day)")
    parser.add_argument("geoip_country_db", help="Name of the MaxMind GeoIP2 country database file in the databases folder")
    parser.add_argument("geoip_city_db", help="Name of the MaxMind GeoIP2 city database file in the databases folder")
    parser.add_argument("geoip_asn_db", help="Name of the MaxMind GeoIP2 ASN database file in the databases folder")
    parser.add_argument("--run-name", help="Optional name for run")
    parser.add_argument("--keep-temp", action="store_true", help="Keep downloaded and extracted files")
    parser.add_argument("--country", nargs="*", help="Country name(s) to filter by (zero or more).")
    parser.add_argument("--city", nargs="*", help="City name(s) to filter by (zero or more).")
    parser.add_argument("--asn", nargs="*", help="ASN(s) to filter by (zero or more).")
    parser.add_argument("--org", nargs="*", help="Organization name(s) to filter by (zero or more).")
    parser.add_argument("--skip-extraction", action="store_true", help="Skip download, extraction and IP extraction steps (use existing IP files)")
    parser.add_argument(
        "--multithreading",
        nargs="?",
        const=4,  
        type=int,
        help="Multithreading; optionally specify number of workers (default: 4)"
    )
    parser.add_argument("--fast", action="store_true", help="Merge IPs after trace-route processing. NOTE: EXPERIMENTAL")
    parser.add_argument("--verbose", default=True, action="store_true", help="Outputs extra information for the filtered IPs, including Country, City and ASN.")

    args = parser.parse_args()

    def normalize_list(lst):
        return [x.strip() for x in lst] if lst else []

    countries = normalize_list(args.country)
    cities = normalize_list(args.city)
    asns = normalize_list(args.asn)
    orgs = normalize_list(args.org)


    # Resolve database paths
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

    run_id = args.run_name or datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = DATA_DIR / run_id

    filter_parts = []
    if countries: filter_parts.append("country_" + "_".join(countries))
    if cities: filter_parts.append("city_" + "_".join(cities))
    if asns: filter_parts.append("asn_" + "_".join(asns))
    if orgs: filter_parts.append("org_" + "_".join(orgs))
    filter_dir_name = "_".join(filter_parts) if filter_parts else "all"

    prepare_dirs(run_dir=run_dir, filter_dir_name=filter_dir_name)

    if not args.url_file and not args.url:
        print("--url-file OR --url required")
        exit(2)
    elif args.url_file and args.url:
        print("--url-file OR --url required. Please provide only one of them.")
        exit(2)

    if not args.url_file:
        args.url_file = "archive_links.txt"
        run_script("extract-links.py", [str(args.url)])

    urls_path = run_dir / "archive_links.txt"
    shutil.copy(args.url_file, urls_path)

    with open(args.url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]


    if args.fast:
        for url in urls:
            try:
                extract_ips(archive_url=url, run_dir=run_dir, skip_extraction=args.skip_extraction)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                print("-" * 60)

        ips = combine_ips_in_dir(dir_name=(run_dir / "ips"))

        results_file = run_dir / f"{run_id}_all_ips.txt" 
        with results_file.open("w", encoding='utf-8') as out:
            for ip in sorted(ips):
                out.write(ip + "\n")

        ip_file = run_dir / f"{run_id}_all_ips.txt"
           
        details_file = run_dir / "ips_plus_details" / f"{run_id}_ips.txt"
        
        results_dir = run_dir / f"{run_id}_{filter_dir_name}_ips.txt" 

        filter_args = [str(details_file), "--output_file", str(results_dir)]
        if countries:
            filter_args.extend(["--country"] + countries)
        if cities:
            filter_args.extend(["--city"] + cities)
        if asns:
            filter_args.extend(["--asn"] + asns)
        if orgs:
            filter_args.extend(["--org"] + orgs)
        if args.verbose:
            filter_args.append("--verbose")

        run_script("extract-details.py", [str(ip_file), "--output_file", str(details_file), str(geoip_country_db_path), str(geoip_city_db_path), str(geoip_asn_db_path)])
        run_script("filters.py", filter_args)
        

    else:
        for url in urls:
            try:
                process(url, run_dir, filter_dir_name, str(geoip_country_db_path), str(geoip_city_db_path), str(geoip_asn_db_path), 
                    countries = countries, cities = cities, asns = asns, orgs = orgs,
                    skip_extraction=args.skip_extraction, fast = args.fast)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                print("-" * 60)

        # Combine IPs from the current filter directory
        combine_ips(run_dir, filter_dir_name)  
