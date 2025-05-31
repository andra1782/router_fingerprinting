from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import pandas as pd

from config import *
from utils import *


def extract_fields(tshark_json):
    try:
        layers = tshark_json[0]['_source']['layers']
        snmp = layers.get('snmp', {})
        tree = snmp.get('snmp.msgAuthoritativeEngineID_tree', {})

        enterprise = tree.get('snmp.engineid.enterprise', '')
        format_id = tree.get('snmp.engineid.format', '')
        mac = tree.get('snmp.engineid.mac', '')
        boots = snmp.get('snmp.msgAuthoritativeEngineBoots', '')
        time_raw = snmp.get('snmp.msgAuthoritativeEngineTime', '')
        uptime = seconds_to_uptime(time_raw) if time_raw else ''
        return enterprise, format_id, mac, boots, uptime

    except Exception as e:
        return '', '', '', '', ''


def process_snmp_row(idx: int, row: pd.Series) -> dict:
    """
    Decode a single ZMap CSV row's SNMP hex payload into structured SNMPv3 engine fields.

    Args:
        idx:   The row index from the original DataFrame (used for naming temp files).
        row:   A pandas Series with at least the keys:
               - "saddr": source IP that responded
               - "data" : hex-encoded SNMP payload string

    Returns:
        A dict with the following keys:
          - "ip"               : same as row["saddr"]
          - "enterprise"       : SNMP engine enterprise OID
          - "engineIDFormat"   : format identifier for the engine ID
          - "engineIDData"     : raw engine ID bytes (MAC portion)
          - "snmpEngineBoots"  : engine boots count
          - "snmpEngineTime"   : engine uptime, formatted as “XdYhZmWs”

        If any subprocess step fails, returns `"ERROR"` for the enterprise field
        and empty strings for all other fields.

    Note:
        - Requires `text2pcap` and `tshark` on PATH.
        - Uses Python's `tempfile.TemporaryDirectory` to isolate and automatically
          delete intermediate `.txt` and `.pcap` files.
    """
    ip = row['saddr']
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        dump_path = tmpdir / f'snmpdump_{idx}.txt'
        pcap_path = tmpdir / f'snmp_packet_{idx}.pcap'
        dump_path.write_text(hex_to_text2pcap_format(row['data']))

        try:
            subprocess.run(
                ['text2pcap', '-q', '-T', '50000,161', dump_path, pcap_path],
                check=True,
                stderr=subprocess.DEVNULL,
            )
            tshark = subprocess.run(
                ['tshark', '-r', pcap_path, '-T', 'json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            tshark_json = json.loads(tshark.stdout.decode())
            enterprise, fmt, mac, boots, uptime = extract_fields(tshark_json)

        except subprocess.CalledProcessError as e:
            print(f'[ERROR] IP {ip}: {e}')
            enterprise = 'ERROR'
            fmt = mac = boots = uptime = ''

        return {
            'ip': ip,
            'enterprise': enterprise,
            'engineIDFormat': fmt,
            'engineIDData': mac,
            'snmpEngineBoots': boots,
            'snmpEngineTime': uptime,
            'country': row['country'],
            'city': row['city'],
            'asn': row['asn'],
            'asn_name': row['asn_name'],
        }

def process_ntp_row(idx: int, row: pd.Series) -> dict:
    """
    Parse the hex-encoded NTP response payload and extract all standard header fields.

    Parameters
    ----------
    idx : int
        Row index (unused, but kept for compatibility).
    row : pandas.Series
        Must contain a 'data' field with the hex-encoded UDP payload, and 'saddr' for source IP.

    Returns
    -------
    dict
        A dict with:
        
        - ip                : str    Source IP (row['saddr'])
        - LI                : int    Leap Indicator (0-3)
        - VN                : int    Version Number (3 bits)
        - Mode              : int    Mode (3 bits)
        - Stratum           : int    Stratum level (0-16)
        - Poll              : int    Poll exponent (log₂ seconds between messages)
        - Precision         : float  Precision in seconds (2^precision)
        - Root_Delay        : float  Round-trip delay to ref clock (seconds)
        - Root_Dispersion   : float  Max error relative to ref clock (seconds)
        - Ref_ID            : str    Reference Identifier (“a.b.c.d” or ASCII tag)
        - Ref_Timestamp     : datetime  Time when local clock was last set
        - Orig_Timestamp    : datetime  Time request departed from the client
        - Recv_Timestamp    : datetime  Time request arrived at the server
        - Tx_Timestamp      : datetime  Time response left the server
    """
    hexstr = row.get('data', '')
    raw = bytes.fromhex(hexstr)
    if len(raw) < 48:
        return {}

    # Byte 0: LI (2 bits), VN (3 bits), Mode (3 bits)
    li_vn_mode, = struct.unpack('!B', raw[0:1])
    LI = (li_vn_mode >> 6) & 0x3
    VN = (li_vn_mode >> 3) & 0x7
    Mode = li_vn_mode & 0x7

    # Byte 1-3
    Stratum = raw[1]
    Poll = raw[2]
    precision_byte = struct.unpack('!b', raw[3:4])[0]
    Precision = 2 ** precision_byte

    # Bytes 4-7, 8-11: root delay & dispersion in 16.16 fixed-point
    rd_int, rd_frac = struct.unpack('!HH', raw[4:8])
    Root_Delay = rd_int + rd_frac / 2**16
    rp_int, rp_frac = struct.unpack('!HH', raw[8:12])
    Root_Dispersion = rp_int + rp_frac / 2**16

    # Bytes 12-15: Reference ID
    ref_id_bytes = raw[12:16]
    Ref_ID = '.'.join(str(b) for b in ref_id_bytes)

    # Helper to convert a 64-bit NTP timestamp to datetime
    def ntp_to_dt(offset):
        sec, frac = struct.unpack('!II', raw[offset:offset+8])
        ntp_epoch = datetime(1900, 1, 1)
        return ntp_epoch + timedelta(seconds=sec,
                                     microseconds=frac * 1e6 / 2**32)

    Ref_Timestamp  = ntp_to_dt(16)
    Orig_Timestamp = ntp_to_dt(24)
    Recv_Timestamp = ntp_to_dt(32)
    Tx_Timestamp   = ntp_to_dt(40)

    return {
        'ip': row.get('saddr'),
        'LI': LI,
        'VN': VN,
        'Mode': Mode,
        'Stratum': Stratum,
        'Poll': Poll,
        'Precision (s)': Precision,
        'Root_Delay (s)': Root_Delay,
        'Root_Dispersion (s)': Root_Dispersion,
        'Ref_ID': Ref_ID,
        'Ref_Timestamp': Ref_Timestamp,
        'Orig_Timestamp': Orig_Timestamp,
        'Recv_Timestamp': Recv_Timestamp,
        'Tx_Timestamp': Tx_Timestamp,
        'country': row['country'],
        'city': row['city'],
        'asn': row['asn'],
        'asn_name': row['asn_name'],
    }

def append_metadata(df: pd.DataFrame, path: Path) -> None:
    """Merges the parsed ZMap dataframe to the corresponding metadata"""
    metadata_path = Path(MetadataFileMapper().get(str(path.resolve())))
    metadata_df = pd.read_csv(metadata_path)
    return pd.merge(df, metadata_df, left_on='saddr', right_on='ip', how='inner')


def parse_results(zmap_csv: str, out_csv: str, scan_mode: ScanMode, max_workers: int = 5, with_metadata: bool = True) -> pd.DataFrame:
    """
    Reads a raw ZMap CSV, decodes each row, and writes the final parsed CSV.

    Args:
        zmap_csv: Path to raw ZMap CSV output.
        out_csv: Path for the final parsed CSV.
        max_workers: Max number of thread workers.
    """
    scan_mode_func = {
        ScanMode.SNMPV3: process_snmp_row,
        ScanMode.NTP: process_ntp_row
    }

    zpath = Path(zmap_csv)
    if not zpath.is_file():
        raise FileNotFoundError(f'ZMap CSV not found: {zmap_csv}')

    df = append_metadata(pd.read_csv(zpath), zpath) if with_metadata else pd.read_csv(zpath)

    records = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(scan_mode_func[scan_mode], idx, row): idx for idx, row in df.iterrows()}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                rec = future.result()
                records.append(rec)
            except Exception as e:
                print(f'[ERROR] processing row {idx} in {zmap_csv}: {e}', file=sys.stderr)

    out_df = pd.DataFrame(records)
    out_df.to_csv(out_csv, index=False)
    print(f'Parsed results written to {out_csv}')
    return out_df


def postprocess(
    *,
    ip_mode: IPMode,
    scan_mode: ScanMode,
    input_dir: str = DEFAULT_ZMAP_PATH,
    out_dir: str = DEFAULT_DECODED_PATH,
    max_workers: int = 5,
    with_metadata: bool = True,
    **kwargs,
) -> None:
    """
    Processes all ZMap CSV files and outputs one parsed CSV per input.
    IPv6 postprocessing is not yet supported.

    Args:
        ip_mode: ipv4 or ipv6.
        scan_mode: snmpv3 or ntp
        input_dir: Directory containing raw IPv4 and IPv6 ZMap CSV files.
        out_dir: Directory to write parsed CSV outputs.
        max_workers: Max number of thread workers.
    """
    ip_dir = (
        Path(input_dir)
        if 'input_dir' in kwargs or input_dir != DEFAULT_ZMAP_PATH
        else Path(input_dir) / f'{ip_mode.value}/filtered'
    )
    if not ip_dir.is_dir():
        raise FileNotFoundError(f'ZMap directory not found: {ip_dir}')

    out_path = Path(out_dir) / f'{ip_mode.value}'
    out_path.mkdir(parents=True, exist_ok=True)

    for csv_path in ip_dir.glob('*.csv'):
        base = csv_path.stem
        out_csv = out_path / f'{base}_parsed.csv'
        try:
            parse_results(zmap_csv=str(csv_path), out_csv=str(out_csv), scan_mode=scan_mode, max_workers=max_workers, with_metadata=with_metadata)
        except Exception as e:
            print(f'Error processing {csv_path.name}: {e}', file=sys.stderr)
            continue

    # TODO: add for ipv6
