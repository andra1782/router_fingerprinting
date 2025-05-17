# ZMAP snmpv3 scanner

Works only with ipv4 (for now).

## Prerequisites
- zmap
- pandas in your env
- need to have extracted the ips, refer to [traceroute extractor README](../traceroute-ip-country-extractor//README.md)

## Run entire pipeline
This will **preprocess** ➔ **scan** ➔ **postprocess** in one go. Your input folder will be the destination where the ips of a specific contry were extracted. If you ran the extractor code with default output args, this path should be: `../traceroute-ip-country-extractor/data/{extracted day}/country_ips/`.
```
python runner.py run-all <mode> <input_dir>
```

Full command:
```
python runner.py run-all <mode> <input_dir> [--out-dir out_dir] [--per-file] [-r rate] [-c cooldown] [--max-workers N]
```
**Required Args:**
- `mode`: defines whether to run IPv4 or IPv6 (`ipv4` or `ipv6`).
- `input_dir`: see above.

**Optional Args:**
- `--out-dir out_dir`: directory for all final outputs. Defaults to `./data/{now}/default_decoded`
- `--per-file`: if set, each ip input file will generate a separate output file. Otherwise, the data will be merged into a single output file. 
- `-r rate`: zmap scan packets-per-second rate. Defaults to 3000.
- `-c cooldown`: for how long will zmap continue receiving. Deafults to 2.
- `--max-workers N`: max number of threading workers for decoding zmap scan results. Defaults to 5.


## Run individual scripts

### To preprocess: 
Split raw ip `.txt` lists in unique ipv4 and ipv6 files. The arguments are the same as in pipeline. The default output path is `./data/{now}/ips`.
```
python runner.py preprocess <input_dir> [--out-dir out_dir] [--per-file]
```

### To run scanner (zmap snmpv3 scan on the ip files):
Run ZMap SNMPv3 against your ip `.txt` files. Default `input_dir` will be the output path of the preprocessor (`./data/{now}/ips`). The default `out_file` will be `./data/{now}/results_encoded`. Here there will be two folders, one for unfiltered data, so zmap's untouched output, and one for only non-empty snmpv3 responses coming from ips in the input list. The rest of the arguments are the same as in pipeline.
```
python runner.py scan-ips <mode> [input_dir] [--out-dir out_dir] [-r rate] [-c cooldown]
```

### To run postprocessor 
Decode the raw ZMap CSVs into a final, human-readable CSV with columns: 
```
ip,enterprise,engineIDFormat,engineIDData,snmpEngineBoots,snmpEngineTime
```
The `input_dir` should be the filtered output folder from the scanner, by default: `./data/{now}/results_encoded/{ip mode}/filtered`. The output will be written in `./data/{now}/results_decoded`. The rest of the arguments are the same as in pipeline.

```
python runner.py postprocess <mode> [input_dir] [--out-dir out_dir] [--max-workers N]
```
