from pathlib import Path
import subprocess
import sys
from typing import Tuple
import pandas as pd
from config import *


def get_subdirs(ip_mode: IPMode, out_dir: Path) -> Tuple[Path, Path]:
    """
    Create and return the unfiltered and filtered output directories for a given IP mode and output base directory.

    Args:
        ip_mode: IPMode.IPV4 or IPMode.IPV6, determines the subdirectory.
        out_dir: Base output directory.

    Returns:
        Tuple containing paths to the unfiltered and filtered output directories.
    """
    dir = Path(out_dir) / f'{IPMode.IPV4.value if ip_mode == IPMode.IPV4 else IPMode.IPV6.value}'

    unfiltered_dir = dir / 'unfiltered'
    filtered_dir = dir / 'filtered'
    unfiltered_dir.mkdir(parents=True, exist_ok=True)
    filtered_dir.mkdir(parents=True, exist_ok=True)

    return unfiltered_dir, filtered_dir


def run_scan(
    *,
    ip_mode: IPMode,
    scan_mode: ScanMode,
    whitelist_dir: str = DEFAULT_IP_PATH,
    out_dir: str = DEFAULT_ZMAP_PATH,
    rate: int = DEFAULT_RATE,
    cooldown: int = DEFAULT_COOLDOWN,
    **kwargs,
) -> None:
    """
    Run a scan for each whitelist file using the specified scan mode (SNMPv3, NTP_ZMAP, or NTP_NMAP).
    - For SNMPv3 and NTP_ZMAP, uses ZMap UDP and filters results by whitelist and data presence.
    - For NTP_NMAP, uses Nmap for OS detection and parses output to CSV.
    - Handles output directory structure and metadata mapping.

    Args:
        ip_mode: IPMode.IPV4 or IPMode.IPV6, controls IPv6 flag and output naming.
        scan_mode: ScanMode.SNMPV3, ScanMode.NTP_ZMAP, or ScanMode.NTP_NMAP.
        whitelist_dir: Directory containing per-input whitelist .txt files.
        out_dir: Output directory for scan results.
        rate: Packets-per-second rate for ZMap (ignored for Nmap).
        cooldown: Cooldown time for ZMap (ignored for Nmap).
        **kwargs: Additional arguments (not used).
    """
    whitelist_path = (
        Path(whitelist_dir)
        if 'whitelist_dir' in kwargs or whitelist_dir != DEFAULT_IP_PATH
        else Path(whitelist_dir) / f'{ip_mode.value}' / 'raw'
    )
    print(whitelist_dir)

    if not whitelist_path.is_dir():
        raise FileNotFoundError(f'Whitelist directory not found: {whitelist_dir}')

    z6_flag = ['-6'] if ip_mode == IPMode.IPV6 else []
    unfiltered_result_dir, filtered_result_dir = get_subdirs(ip_mode=ip_mode, out_dir=Path(out_dir))

    for file_path in whitelist_path.glob('*.txt'):
        try:
            if file_path.stat().st_size == 0:
                print(f'Skipping empty whitelist file: {file_path.name}')
                continue
        except OSError as e:
            print(f'Warning: could not check file size for {file_path.name}: {e}', file=sys.stderr)
            continue

        ip_file = str(file_path.resolve())
        unfiltered_output_csv = unfiltered_result_dir / f'zmap_{scan_mode.value}_{file_path.stem}.csv'
        filtered_output_csv = filtered_result_dir / f'zmap_{scan_mode.value}_{file_path.stem}.csv'

        if scan_mode == ScanMode.NTP_NMAP:
            # Nmap NTP OS scan
            nmap_output = unfiltered_result_dir / f'nmap_{file_path.stem}.txt'
            nmap_cmd = [
                'sudo', 'nmap', '-sU', '-p', '123', '-O', '-iL', ip_file, '-oN', str(nmap_output)
            ]
            print(f'Running Nmap NTP OS scan on {file_path.name} -> {nmap_output.name}')
            try:
                subprocess.run(nmap_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                print(f'Error running Nmap on {ip_file}: {e}', file=sys.stderr)
                continue
            # Parse Nmap output and save as CSV
            try:
                results = []
                with open(nmap_output, 'r') as f:
                    lines = f.readlines()
                ip = None
                os = None
                ports = []
                extra = {}
                for line in lines:
                    if line.startswith('Nmap scan report for'):
                        if ip:
                            results.append({'ip': ip, 'os': os, 'ports': ';'.join(ports), **extra})
                        ip = line.split()[-1]
                        os = None
                        ports = []
                        extra = {}
                    elif line.strip().startswith('OS details:'):
                        os = line.strip().replace('OS details: ', '')
                    elif line.strip().startswith('OS guesses:'):
                        extra['os_guesses'] = line.strip().replace('OS guesses: ', '')
                    elif line.strip().startswith('Aggressive OS guesses:'):
                        extra['os_aggressive_guesses'] = line.strip().replace('Aggressive OS guesses: ', '')
                    elif line.strip().startswith('Service Info:'):
                        extra['service_info'] = line.strip().replace('Service Info: ', '')
                    elif line.strip().startswith('123/udp'):
                        ports.append(line.strip())
                if ip:
                    results.append({'ip': ip, 'os': os, 'ports': ';'.join(ports), **extra})
                import pandas as pd
                df = pd.DataFrame(results)
                df.to_csv(unfiltered_output_csv, index=False)
                # For NTP NMAP, filtered = unfiltered (all IPs scanned)
                df.to_csv(filtered_output_csv, index=False)
                print(f'Nmap results saved: {len(df)} rows in {filtered_output_csv.name}')
                MetadataFileMapper().set(
                    str(unfiltered_output_csv.resolve()), MetadataFileMapper().get(ip_file)
                )
                MetadataFileMapper().set(
                    str(filtered_output_csv.resolve()), MetadataFileMapper().get(ip_file)
                )
            except Exception as e:
                print(f"Warning: could not parse Nmap output {nmap_output.name}: {e}", file=sys.stderr)
        
        else: 
            # ZMap scan for SNMPv3 or NTP
            cmd = [
                'sudo',
                'zmap',
                *z6_flag,
                '-M',
                'udp',
                '-p',
                scan_mode.port,
                f'--probe-args=file:{scan_mode.packet}',
                '-O',
                'csv',
                '-f',
                '*',
                '-o',
                str(unfiltered_output_csv),
                '-r',
                str(rate),
                '-c',
                str(cooldown),
                '-w',
                ip_file,
            ]

            print(f'Running ZMap scan ({ip_mode}) on {file_path.name} -> {unfiltered_output_csv.name}')
            try:
                subprocess.run(cmd, check=True)
                print(f'Scan complete: {unfiltered_output_csv}')
            except subprocess.CalledProcessError as e:
                print(f'Error running ZMap on {ip_file}: {e}', file=sys.stderr)

            # FILTER RESULTS: keep only IPs in our whitelist and remove rows with empty data
            try:
                whitelist_ips = {
                    line.strip() for line in file_path.resolve().read_text().splitlines() if line.strip()
                }
                df = pd.read_csv(unfiltered_output_csv)
                filtered = df[df['saddr'].isin(whitelist_ips)].dropna(subset=['data'])
                filtered.to_csv(filtered_output_csv, index=False)
                print(f'Filtered results: {len(filtered)} rows kept in {filtered_output_csv.name}')

                MetadataFileMapper().set(
                    str(unfiltered_output_csv.resolve()), MetadataFileMapper().get(ip_file)
                )
                MetadataFileMapper().set(
                    str(filtered_output_csv.resolve()), MetadataFileMapper().get(ip_file)
                )

            except Exception as e:
                print(f"Warning: could not filter {filtered_output_csv.name}: {e}", file=sys.stderr)
