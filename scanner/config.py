from datetime import datetime
from enum import StrEnum, auto
import ipaddress
import json
from functools import *
from pathlib import Path
from utils import *


class IPMode(StrEnum):
    IPV6 = auto()
    IPV4 = auto()

    @property
    def address(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        mapping = {IPMode.IPV4: ipaddress.IPv4Address, IPMode.IPV6: ipaddress.IPv6Address}
        return mapping[self]
    
class ScanMode(StrEnum):
    SNMPV3 = auto()
    NTP = auto()

    @property
    def packet(self) -> str:
        mapping={ScanMode.SNMPV3: 'snmp3_161.pkt', ScanMode.NTP: 'ntp_123.pkt'}
        return mapping[self]

    @property
    def port(self) -> str:
        mapping={ScanMode.SNMPV3: '161', ScanMode.NTP: '123'}
        return mapping[self]

#####################################################################################################
# Default flags
#####################################################################################################

# zmap
DEFAULT_RATE = 3000
DEFAULT_COOLDOWN = 2

# postprocessing
DEFAULT_WORKERS = 5

#####################################################################################################
# Default output paths
#####################################################################################################

now = datetime.now().strftime('%Y_%m_%d_%H')
DEFAULT_DATA_PREFIX = f'data/{now}'
DEFAULT_IP_PATH = f'{DEFAULT_DATA_PREFIX}/ips'
DEFAULT_ZMAP_PATH = f'{DEFAULT_DATA_PREFIX}/results_encoded'
DEFAULT_DECODED_PATH = f'{DEFAULT_DATA_PREFIX}/results_decoded'

#####################################################################################################
# File Mapper
#####################################################################################################


class MetadataFileMapper(metaclass=Singleton):
    data_to_metadata = {}

    metadata_map_file = Path(DEFAULT_DATA_PREFIX) / 'metadata_map.json'

    @classmethod
    def set(cls, data_file: str, metadata_file: str, store: bool = False):
        cls.data_to_metadata[data_file] = metadata_file
        if store:
            cls.save_metadata(data_file=data_file, metadata_file=metadata_file)

    @classmethod
    def get(cls, data_file: str):
        return cls.data_to_metadata.get(data_file) or cls.get_from_file(data_file)

    @classmethod
    def save_metadata(cls, data_file: str, metadata_file: str):
        cls.metadata_map_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cls.metadata_map_file, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[data_file] = metadata_file
        with open(cls.metadata_map_file, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def get_from_file(cls, data_file: str) -> str:
        try:
            with open(cls.metadata_map_file, 'r') as f:
                content = f.read()
                return json.loads(content).get(data_file)
        except:
            return None
