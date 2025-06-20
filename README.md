# router_fingerprinting

Collection of scripts allowing the fingerprinting of routers towards research purposes. 

Pipeline:
Collect IPs through traceroutes -> Get information about IPs (location, ASN) -> SNMP/NTP requests -> Extract information from responses -> Address resolution -> Infer whether routers are vulnerable based on uptime

![Pipeline](pipeline.png)

## Prerequisites
```bash
pip install -r requirements.txt
```

## System requirements for the scanner
```bash
sudo apt install zmap
sudo apt install nmap
sudo apt install wireshark-common
sudo apt install wireshark-common tshark
```