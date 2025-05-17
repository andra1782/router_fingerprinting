import ipaddress
from pathlib import Path
import re
import sys
from typing import List
from config import *


def write_ips(out_dir: str, filename: str, ip_list: List[str], mode: IPMode) -> str:
    ip_dir = Path(out_dir) / f'{mode.value}'
    ip_dir.mkdir(parents=True, exist_ok=True)
    ip_out = ip_dir / f"{filename}_{mode.value}.txt"

    if ip_list:
        ip_out.write_text("\n".join(ip_list) + "\n")
    else:
        ip_out.write_text("")
    return ip_out.name


def split_ips(input_dir: str, out_dir: str = DEFAULT_IP_PATH, per_file: bool = False) -> None:
    """
    Read all '.txt' files in `input_dir`, split their contents into unique
    IPv4 and IPv6 addresses, and write them out under `out_dir`.

    Args:
        input_dir (str): Path to a directory containing one or more '.txt'
            files, each with one IP address per line.
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
    
    ipv4_list = []
    ipv6_list = []
    filename = ''
    for file_path in input_path.glob('*.txt'):
        if per_file: 
            ipv4_list = []
            ipv6_list = []

        with file_path.open('r') as infile:
            for line in infile:
                ip_str = line.strip()
                if not ip_str: 
                    continue
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    if isinstance(ip_obj, ipaddress.IPv4Address) and ip_str not in ipv4_list:
                        ipv4_list.append(ip_str)
                    elif isinstance(ip_obj, ipaddress.IPv6Address) and ip_str not in ipv6_list:
                        ipv6_list.append(ip_str)
                except ValueError:
                    print(
                        f"Warning: skipping invalid IP '{ip_str}' in {file_path.name}",
                        file=sys.stderr
                    )
        filename = re.sub(r'(?:^traceroute-)|(?:^|_)ips(?:_|$)', '_', file_path.stem).strip('_')
        if per_file:
            v4_out_name = write_ips(out_dir=out_dir, filename=filename, ip_list=ipv4_list, mode=IPMode.IPV4)
            v6_out_name = write_ips(out_dir=out_dir, filename=filename, ip_list=ipv6_list, mode=IPMode.IPV6)
            print(
                f"Processed {file_path.name}: wrote {len(ipv4_list)} IPv4 to {v4_out_name},"
                f" {len(ipv6_list)} IPv6 to {v6_out_name}"
            )
    if not per_file:
        write_ips(out_dir=out_dir, filename=re.sub(r'T\d{4}', '', filename), ip_list=ipv6_list, mode=IPMode.IPV6)
        write_ips(out_dir=out_dir, filename=re.sub(r'T\d{4}', '', filename), ip_list=ipv4_list, mode=IPMode.IPV4)

