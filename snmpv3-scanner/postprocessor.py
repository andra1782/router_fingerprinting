from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pandas as pd

from config import *
from utils import *


def extract_fields(tshark_json):
    try:
        layers = tshark_json[0]["_source"]["layers"]
        snmp = layers.get("snmp", {})
        tree = snmp.get("snmp.msgAuthoritativeEngineID_tree", {})

        enterprise = tree.get("snmp.engineid.enterprise", "")
        format_id = tree.get("snmp.engineid.format", "")
        mac = tree.get("snmp.engineid.mac", "")
        boots = snmp.get("snmp.msgAuthoritativeEngineBoots", "")
        time_raw = snmp.get("snmp.msgAuthoritativeEngineTime", "")
        uptime = seconds_to_uptime(time_raw) if time_raw else ""
        return enterprise, format_id, mac, boots, uptime

    except Exception as e:
        return "", "", "", "", ""
    

def process_row(idx: int, row: pd.Series) -> dict:
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
    ip = row["saddr"]
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        dump_path = tmpdir / f"snmpdump_{idx}.txt"
        pcap_path = tmpdir / f"snmp_packet_{idx}.pcap"
        dump_path.write_text(hex_to_text2pcap_format(row["data"]))

        try:
            subprocess.run(
                ["text2pcap", "-q", "-T", "50000,161", dump_path, pcap_path],
                check=True,
                stderr=subprocess.DEVNULL
            )
            tshark = subprocess.run(
                ["tshark", "-r", pcap_path, "-T", "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            tshark_json = json.loads(tshark.stdout.decode())
            enterprise, fmt, mac, boots, uptime = extract_fields(tshark_json)

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] IP {ip}: {e}")
            enterprise = "ERROR"
            fmt = mac = boots = uptime = ""

        return {
            "ip": ip,
            "enterprise": enterprise,
            "engineIDFormat": fmt,
            "engineIDData": mac,
            "snmpEngineBoots": boots,
            "snmpEngineTime": uptime,
        }

def parse_results(zmap_csv: str, out_csv: str, max_workers: int = 5) -> None:
    """
    Reads a raw ZMap CSV, decodes each row, and writes the final parsed CSV.

    Args:
        zmap_csv: Path to raw ZMap CSV output.
        out_csv: Path for the final parsed CSV.
        max_workers: Max number of thread workers.
    """
    zpath = Path(zmap_csv)
    if not zpath.is_file():
        raise FileNotFoundError(f"ZMap CSV not found: {zmap_csv}")

    df = pd.read_csv(zpath)

    records = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(process_row, idx, row): idx
            for idx, row in df.iterrows()
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                rec = future.result()
                records.append(rec)
            except Exception as e:
                print(f"[ERROR] processing row {idx} in {zmap_csv}: {e}", file=sys.stderr)

    out_df = pd.DataFrame(records)
    out_df.to_csv(out_csv, index=False)
    print(f"Parsed results written to {out_csv}")

def postprocess(mode: IPMode, input_dir: str = DEFAULT_ZMAP_PATH, out_dir: str = DEFAULT_DECODED_PATH, max_workers: int = 5) -> None:
    """
    Processes all ZMap CSV files and outputs one parsed CSV per input.
    IPv6 postprocessing is not yet supported.

    Args:
        mode: ipv4 or ipv6.
        input_dir: Directory containing raw IPv4 and IPv6 ZMap CSV files.
        out_dir: Directory to write parsed CSV outputs.
        max_workers: Max number of thread workers.
    """
    ip_dir = Path(input_dir) / f'{mode.value}/filtered'
    if not ip_dir.is_dir():
        raise FileNotFoundError(f"ZMap directory not found: {ip_dir}")

    out_path = Path(out_dir) / f'{mode.value}'
    out_path.mkdir(parents=True, exist_ok=True)

    for csv_path in ip_dir.glob('*.csv'):
        base = csv_path.stem
        out_csv = out_path / f"{base}_parsed.csv"
        try:
            parse_results(zmap_csv=str(csv_path), out_csv=str(out_csv), max_workers=max_workers)
        except Exception as e:
            print(f"Error processing {csv_path.name}: {e}", file=sys.stderr)
            continue
    
    #TODO: add for ipv6

if __name__ == '__main__':
    parse_results('test.csv', 'test_res.csv')
