# ZMAP snmpv3 scanner

Works only with ipv4 (for now).

## Pre-requisites
- Zmap:
```bash
sudo apt install zmap
sudo apt install nmap
sudo apt install wireshark-common
sudo apt install wireshark-common tshark
```
- pandas in your env
- need to have extracted the ips, refer to [traceroute extractor README](../traceroute-ip-country-extractor//README.md)


## Run entire pipeline
This will **preprocess** ➔ **scan** ➔ **postprocess** in one go. Your input folder will be the destination where the ips of a specific contry were extracted. If you ran the extractor code with default output args, this path should be: `../traceroute-ip-country-extractor/data/{extracted day}/results/`.
```
python runner.py run-all <ipmode> <scanmode> <input_dir>
```

Full command:
```
python runner.py run-all <ipmode> <scanmode> <input_dir> [--out-dir out_dir] [--per-file] [-r rate] [-c cooldown] [--max-workers N]
```
**Required Args:**
- `ipmode`: defines whether to run IPv4 or IPv6 (`ipv4` or `ipv6`).
- `scanmode`: definsed whether to scan SNMPv3 or NTP
- `input_dir`: see above.

**Optional Args:**
- `--out-dir out_dir`: directory for all final outputs. Defaults to `./data/{now}/results_decoded`
- `--per-file`: if set, each ip input file will generate a separate output file. Otherwise, the data will be merged into a single output file. 
- `-r rate`: zmap scan packets-per-second rate. Defaults to 3000.
- `-c cooldown`: for how long will zmap continue receiving. Deafults to 2.
- `--max-workers N`: max number of threading workers for decoding zmap scan results. Defaults to 5.


## Run individual scripts

### To preprocess: 
Split ip lists in unique ipv4 and ipv6 files. The arguments are the same as in pipeline. The default output path is `./data/{now}/ips`. This will contain two folders: `raw` with just the ip `.txt` files and `metadata` with `.csv` files containing the ips and the corresponding metadata.
```
python runner.py preprocess <input_dir> [--out-dir out_dir] [--per-file]
```

### To run scanner (zmap snmpv3 scan on the ip files):
Run ZMap SNMPv3 against your ip `.txt` files. Default `input_dir` will be the output path of the preprocessor (`./data/{now}/ips/raw`). The default `out_file` will be `./data/{now}/results_encoded`. Here there will be two folders, one for unfiltered data, so zmap's untouched output, and one for only non-empty snmpv3 responses coming from ips in the input list. The rest of the arguments are the same as in pipeline.
```
python runner.py scan-ips <ipmode> <scanmode> [input_dir] [--out-dir out_dir] [-r rate] [-c cooldown]
```

### To run postprocessor 
Decode the raw ZMap CSVs into a final, human-readable CSV with columns: 
```
ip,enterprise,engineIDFormat,engineIDData,snmpEngineBoots,snmpEngineTime,country,city,asn,asn_name 
```
The `input_dir` should be the filtered output folder from the scanner, by default: `./data/{now}/results_encoded/{ip mode}/filtered`. The output will be written in `./data/{now}/results_decoded`. The rest of the arguments are the same as in pipeline.

```
python runner.py postprocess <ipmode> <scanmode> --input_dir [input_dir] [--out-dir out_dir] [--max-workers N]
```

## Plotting scripts

### `statistics_per_country.py`

This script analyzes router scan results and traceroute data to generate statistics and plots per country. It loads a CSV file with scan results and a directory of TXT files with traceroute results, then produces plots (e.g., max IPs per engineId) in the specified output directory.

**Usage:**
```
python statistics_per_country.py <csv_file> <txt_dir> [--output-dir OUTPUT_DIR]
```
- `<csv_file>`: Path to the input CSV file (scanner results).
- `<txt_dir>`: Path to the directory containing TXT files (traceroute results).
- `--output-dir` or `-o`: (Optional) Output directory for the plots. Defaults to `plots`.

---

### `statistics_outage.py`

**Description:**  
This script analyzes router reboot data during a specified outage period. It reads a CSV file with scan results, calculates reboot times, and generates two plots: one for IPs and one for unique routers that rebooted during the outage. The specific outage which we analyzed in this script is the one in Spain on the 28th of April 2025 at 12:33.

**Usage:**
```
python statistics_outage.py <input_file> [--output OUTPUT] [--collection-time TIME] [--outage-start TIME] [--outage-end TIME]
```
- `<input_file>`: Path to the input CSV file (scanner results).
- `--output` or `-o`: (Optional) Output file path prefix for the plots. Default: `plots/outage_reboots.png` (will create `outage_reboots_ips.png` and `outage_reboots_routers.png`).
- `--collection-time`: (Optional) Collection time in format `YYYY-MM-DD HH:MM:SS`. Default: `2025-06-16 15:00:00`.
- `--outage-start`: (Optional) Outage start time. Default: `2025-04-28 12:00:00`.
- `--outage-end`: (Optional) Outage end time. Default: `2025-04-29 23:59:59`.


