from collections import defaultdict
import ipaddress
from pathlib import Path
import pandas as pd
import re
import sys
from typing import List
from config import *


def write_ips(out_dir: str, filename: str, ip_data: List[str], mode: IPMode, store_mapping: bool = False) -> None:
    ip_dir_raw = Path(out_dir) / f'{mode.value}' / 'raw'
    ip_dir_raw.mkdir(parents=True, exist_ok=True)

    ip_dir_data = Path(out_dir) / f'{mode.value}' / 'metadata'
    ip_dir_data.mkdir(parents=True, exist_ok=True)

    # Write raw ip_data to txt file 
    ip_out_raw = ip_dir_raw / f"{filename}_{mode.value}.txt"
    ip_out_raw.write_text("\n".join(ip_data[mode]['raw']) + "\n")
    print(
        f"Processed raw {mode.value} {ip_out_raw.name}: wrote {len(ip_data[mode.value]['raw'])} unique values."
    )

    # Write ip with metadata to csv
    ip_out_data = ip_dir_data / f"{filename}_{mode.value}.csv"    
    pd.DataFrame(ip_data[mode]['data']).to_csv(ip_out_data, index=False)

    # Create mapping between the raw and metadata files
    MetadataFileMapper().set(data_file=str(ip_out_raw.resolve()), metadata_file=str(ip_out_data.resolve()), store=store_mapping)

def split_ips(input_dir: str, out_dir: str = DEFAULT_IP_PATH, per_file: bool = False, store_mapping: bool = False) -> None:
    """
    Read all '.txt' files in `input_dir`, split their contents into unique
    IPv4 and IPv6 addresses, and write them out under `out_dir`. The outputs will be 
    - txt files with raw ips
    - csv files with ip, country, city, asn, asn_name values

    Args:
        input_dir (str): Path to a directory containing one or more '.txt'
            files, each with one IP address, country, city, asn, asn_name per line, comma separated.
        out_dir (str): Path to the directory under which two subdirectories
            ('ipv4' and 'ipv6') will be created. Defaults to DEFAULT_IP_PATH.
        per_file (bool): If True, reset and write separate IPv4/IPv6 files
            for each input file. If False, accumulate across all files and
            produce two aggregate files at the end.

    Raises:
        FileNotFoundError: If `input_dir` does not exist or is not a directory.
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    ip_data = {mode: {'raw': [], 'data': []} for mode in IPMode}
    filename = ''
    for file_path in input_path.glob('*.txt'):
        if per_file: 
            ip_data = defaultdict(list, ip_data)

        with file_path.open('r') as infile:
            for line in infile:
                ip_str, country, city, asn, asn_name = line.strip().split(',', 4)
                if not ip_str: 
                    continue
                try:
                    for mode in IPMode:           
                        if isinstance(ipaddress.ip_address(ip_str), mode.address) and ip_str not in ip_data[mode]['raw']:
                            ip_data[mode]['raw'].append(ip_str)
                            ip_data[mode]['data'].append({
                                'ip': ip_str,
                                'country': country,
                                'city': city,
                                'asn': asn,
                                'asn_name': asn_name
                            })
                except ValueError:
                    print(
                        f"Warning: skipping invalid IP '{ip_str}' in {file_path.name}",
                        file=sys.stderr
                    )
        filename = re.sub(r'(?:^traceroute-)|(?:^|_)ips(?:_|$)', '_', file_path.stem).strip('_')
        if per_file:
            write_ips(out_dir=out_dir, filename=filename, ip_data=ip_data, mode=IPMode.IPV4, store_mapping=store_mapping)
            write_ips(out_dir=out_dir, filename=filename, ip_data=ip_data, mode=IPMode.IPV6, store_mapping=store_mapping)
            
    if not per_file:
        write_ips(out_dir=out_dir, filename=re.sub(r'T\d{4}', '', filename), ip_data=ip_data, mode=IPMode.IPV6, store_mapping=store_mapping)
        write_ips(out_dir=out_dir, filename=re.sub(r'T\d{4}', '', filename), ip_data=ip_data, mode=IPMode.IPV4, store_mapping=store_mapping)

