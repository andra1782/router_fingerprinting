# router_fingerprinting

TODO

Collection of scripts allowing the fingerprinting of routers towards research purposes. 

Pipeline:
Collect IPs through traceroutes -> Get information about IPs (location, ASN) -> SNMP requests -> Extract information from responses -> Address resolution -> Infer whether routers are vulnerable based on uptime

## Prerequisites
```bash
pip install -r requirements.txt
```

## System requirements for the scanner
```bash
sudo apt install wireshark-common
sudo apt install wireshark-common tshark
```