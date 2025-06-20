# Router Fingerprinting Scanner

This is the second part of our pipeline. It provides large-scale router fingerprinting using ZMap and Nmap, supporting SNMPv3 and NTP (including Nmap OS detection). The pipeline includes preprocessing, scanning, postprocessing, and plotting scripts.

## Prerequisites
- A Linux-based system (Windows not supported). WSL works fine too.
- Python 3.8+
- [zmap](https://zmap.io/)
```bash
sudo apt install zmap
```
- [nmap](https://nmap.org/)
```bash
sudo apt install nmap
```
- pandas 
```bash
pip install pandas
```
- For SNMPv3 postprocessing: `text2pcap` and `tshark` for SNMPv3 decoding
```bash
sudo apt install wireshark-common
sudo apt install wireshark-common tshark
```
- Extracted IPs with metadata (see [traceroute extractor README](../traceroute-ip-country-extractor/README.md))

---

## Pipeline Overview
1. **Preprocess**: Split raw IP lists into unique IPv4/IPv6 files and generate metadata.
2. **Scan**: Run ZMap (SNMPv3/NTP) or Nmap (NTP OS detection) on the IPs.
3. **Postprocess**: Decode and enrich scan results into human-readable CSVs.
4. (Optional) **Plotting**: Analyze and visualize results.

---

## Running the Pipeline

### Full Pipeline (except plotting)
Run all steps in sequence, **preprocess** ➔ **scan** ➔ **postprocess** in one go. Your input folder will be the destination where the ips and the associated metadata were (country, city, asn, org, see the [traceroute extractor README](../traceroute-ip-country-extractor/README.md) for more details). 
```sh
python runner.py run-all <ipmode> <scanmode> <input_dir> [--out-dir out_dir] [--per-file] [-r rate] [-c cooldown] [--max-workers N]
```
- `ipmode`: `ipv4` or `ipv6`
- `scanmode`: `snmpv3`, `ntp_zmap`, or `ntp_nmap`
- `input_dir`: Directory with raw IP lists (see extractor output)
- (Optional) `--out-dir`: Output directory (default: `./data/{now}/results_decoded`)
- (Optional) `--per-file`: Generate separate output per input file
- (Optional) `-r`: ZMap packets-per-second rate (default: 3000)
- (Optional) `-c`: ZMap cooldown (default: 2)
- (Optional) `--max-workers`: Threading workers for decoding (default: 5)

---

### Preprocessing
Split IP lists (in unique ipv4 and ipv6) and generate metadata. The arguments are the same as in pipeline. The default output path is `./data/{now}/ips`. This will contain two folders: raw with just the ip `.txt` files and metadata with `.csv` files containing the ips and the corresponding metadata.

```sh
python runner.py preprocess <input_dir> [--out-dir out_dir] [--per-file]
```
- Output: `./data/{now}/ips/raw` (IP .txt files), `./data/{now}/ips/metadata` (CSV with IP and metadata)

---

### Scanning
Run ZMap or Nmap on the IP files. Default input_dir will be the output path of the preprocessor (./data/{now}/ips/raw). The default out_file will be ./data/{now}/results_encoded. 
```sh
python runner.py scan-ips <ipmode> <scanmode> [input_dir] [--out-dir out_dir] [-r rate] [-c cooldown]
```
- `scanmode` options:
  - `snmpv3`: ZMap SNMPv3 scan
  - `ntp_zmap`: ZMap NTP scan
  - `ntp_nmap`: Nmap NTP OS detection scan

**Output:**
- Unfiltered and filtered CSVs in `./data/{now}/results_encoded/{ipmode}/unfiltered` and `filtered`

---

### Postprocessing
Decode the raw ZMap CSVs (only for ZMap scans) and enrich scan results. The input_dir should be the filtered output folder from the scanner, by default: `./data/{now}/results_encoded/{ip mode}/filtered`. The output will be written in `./data/{now}/results_decoded`. The rest of the arguments are the same as in pipeline.
```sh
python runner.py postprocess <ipmode> <scanmode> --input_dir [input_dir] [--out-dir out_dir] [--max-workers N]
```
- For SNMPv3/NTP (ZMap):  
  Output columns:  
  `ip,enterprise,engineIDFormat,engineIDData,snmpEngineBoots,snmpEngineTime,country,city,asn,asn_name`
- For NTP (Nmap):  
  Output columns:  
  `ip,os,ports,os_guesses,os_aggressive_guesses,service_info,country,city,asn,asn_name`  
  (Some columns may be empty if not detected.)

---

## Plotting Scripts

### `statistics_per_country.py`
Analyze scan results and traceroute data to generate per-country statistics and plots.
```sh
python statistics_per_country.py <csv_file> <txt_dir> [--output-dir OUTPUT_DIR]
```
- `<csv_file>`: Path to the input CSV file (scanner results).
- `<txt_dir>`: Path to the directory containing TXT files (traceroute results).
- `--output-dir` or `-o`: (Optional) Output directory for the plots. Defaults to `plots`.

---

### `statistics_outage.py`
Analyze router reboot data during a specified outage period.
```sh
python statistics_outage.py <input_file> [--output OUTPUT] [--collection-time TIME] [--outage-start TIME] [--outage-end TIME]
```
- `<input_file>`: Path to the input CSV file (scanner results).
- `--output` or `-o`: (Optional) Output file path prefix for the plots. Default: `plots/outage_reboots.png` (will create `outage_reboots_ips.png` and `outage_reboots_routers.png`).
- `--collection-time`: (Optional) Collection time in format `YYYY-MM-DD HH:MM:SS`. Default: `2025-06-16 15:00:00`.
- `--outage-start`: (Optional) Outage start time. Default: `2025-04-28 12:00:00`.
- `--outage-end`: (Optional) Outage end time. Default: `2025-04-29 23:59:59`.

---

## Notes
- IPv6 testing has not worked on the machines and networks that we had access to. This pipeline step has been thoroughly tested for IPv4. 
- For Nmap NTP OS detection, the scanner will attempt to extract all interesting fields from the Nmap output, including OS details, guesses, service info, and open ports.
- All output CSVs will include the metadata columns from the traceroute extraction step(`country`, `city`, `asn`, `asn_name`) if available.
- For more details on the traceroute extraction step, see the [traceroute extractor README](../traceroute-ip-country-extractor/README.md).
