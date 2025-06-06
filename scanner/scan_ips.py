from pathlib import Path
import subprocess
import sys
from typing import Tuple

import pandas as pd
from config import *


def get_subdirs(ip_mode: IPMode, out_dir: Path) -> Tuple[Path, Path]:
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
    Runs ZMap UDP snmpv3 scans on each whitelist file.

    Args:
        whitelist_dir: Directory containing per-input whitelist .txt files.
        ip_mode: IPMode.IPV4 or IPMode.IPV6, controls IPv6 flag and output naming.
        scan_mode: scan mode.
        rate: packets-per-second rate for ZMap.
        cooldown: how long to continue receiving after sending has completed.
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
