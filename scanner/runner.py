import argparse
import sys
from preprocessor import *
from postprocessor import *
from scan_ips import *
from config import *
import pandas as pd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SNMPv3 Scanner Pipeline')
    subparsers = parser.add_subparsers(title='Commands', dest='command', required=True)

    # Preprocess: split raw IP lists into IPv4 and IPv6
    p_pre = subparsers.add_parser('preprocess', help='Split IP files into IPv4 and IPv6 whitelists')
    p_pre.add_argument('input_dir', help='Directory containing raw .txt IP lists')
    p_pre.add_argument(
        '--out-dir', default=DEFAULT_IP_PATH, help='Output directory for split files'
    )
    p_pre.add_argument(
        '--per-file',
        action='store_true',
        default=False,
        help='If set, each input file will generate two output files. Else, all input files will be merged.',
    )

    # Scan: run ZMap on whitelists
    p_scan = subparsers.add_parser('scan-ips', help='Run ZMap scans on IP whitelists')
    p_scan.add_argument('ipmode', help='ipv4 or ipv6')
    p_scan.add_argument('scanmode', help='snmpv3, ntp_zmap, or ntp_nmap')
    p_scan.add_argument(
        '--input_dir', default=DEFAULT_IP_PATH, help='Directory with IPv4 and IPv6 whitelist files'
    )
    p_scan.add_argument(
        '--out-dir',
        default=DEFAULT_ZMAP_PATH,
        help='Output directory for encoded zmap scan results',
    )
    p_scan.add_argument(
        '--rate', '-r', type=int, default=DEFAULT_RATE, help='Packets-per-second rate for ZMap'
    )
    p_scan.add_argument(
        '--cooldown', '-c', type=int, default=DEFAULT_COOLDOWN, help='Cooldown time for ZMap'
    )

    # Postprocess: parse raw ZMap CSV into final CSV
    p_post = subparsers.add_parser('postprocess', help='Parse ZMap CSV into final parsed CSV')
    p_post.add_argument('ipmode', help='ipv4 or ipv6')
    p_post.add_argument('scanmode', help='snmpv3 or ntp')
    p_post.add_argument(
        '--input_dir',
        default=DEFAULT_ZMAP_PATH,
        help='Path to encoded ZMap CSV outputs for IPv4 and/or IPv6 scans',
    )
    p_post.add_argument(
        '--out-dir', default=DEFAULT_DECODED_PATH, help='Path for the final parsed CSV'
    )
    p_post.add_argument(
        '--max-workers',
        type=int,
        default=DEFAULT_WORKERS,
        help='Maximum amount of threading workers.',
    )

    # All: full pipeline
    p_all = subparsers.add_parser(
        'run-all', help='Run preprocess, scan-ipv4, scan-ipv6, and postprocess in one go'
    )
    p_all.add_argument('ipmode', help='ipv4 or ipv6')
    p_all.add_argument('scanmode', help='snmpv3 or ntp')
    p_all.add_argument('input_dir', nargs='?', help='Directory containing raw .txt IP lists')
    p_all.add_argument(
        '--out-dir', default=DEFAULT_DECODED_PATH, help='Base directory for all final outputs'
    )
    p_all.add_argument(
        '--rate',
        '-r',
        type=int,
        default=DEFAULT_RATE,
        help='Packets-per-second rate for ZMap scans',
    )
    p_all.add_argument(
        '--cooldown', '-c', type=int, default=DEFAULT_COOLDOWN, help='Cooldown time for ZMap'
    )
    p_all.add_argument(
        '--max-workers',
        type=int,
        default=DEFAULT_WORKERS,
        help='Maximum amount of threading workers when decoding the scan results.',
    )
    p_all.add_argument(
        '--per-file',
        action='store_true',
        default=False,
        help='If set, each input file will generate an output file. Else, all input files will be merged.',
    )
    args = parser.parse_args()

    if args.command == 'preprocess':
        split_ips(input_dir=args.input_dir, out_dir=args.out_dir, per_file=args.per_file, store_mapping=True)

    elif args.command == 'scan-ips':
        run_scan(
            whitelist_dir=args.input_dir,
            out_dir=args.out_dir,
            ip_mode=IPMode[args.ipmode.upper()],
            scan_mode=ScanMode[args.scanmode.upper()],
            rate=args.rate,
        )

    elif args.command == 'postprocess':
        postprocess(
            input_dir=args.input_dir,
            out_dir=args.out_dir,
            ip_mode=IPMode[args.ipmode.upper()],
            scan_mode=ScanMode[args.scanmode.upper()],
            max_workers=args.max_workers,
            with_metadata=False
        )

    elif args.command == 'run-all':
        split_ips(input_dir=args.input_dir, per_file=args.per_file)
        run_scan(ip_mode=IPMode[args.ipmode.upper()], scan_mode=ScanMode[args.scanmode.upper()], rate=args.rate, cooldown=args.cooldown)
        postprocess(
            out_dir=args.out_dir, ip_mode=IPMode[args.ipmode.upper()], scan_mode=ScanMode[args.scanmode.upper()], max_workers=args.max_workers
        )
    else:
        parser.print_help()
        sys.exit(1)
