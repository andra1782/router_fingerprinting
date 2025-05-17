from datetime import datetime
from enum import StrEnum, auto


class IPMode(StrEnum):
    IPV6 = auto()
    IPV4 = auto()

#####################################################################################################
# Default flags
#####################################################################################################

# zmap
DEFAULT_RATE = 3000
DEFAULT_COOLDOWN = 2

#postprocessing
DEFAULT_WORKERS = 5

#####################################################################################################
# Default output paths 
#####################################################################################################

now = datetime.now().strftime("%Y_%m_%d_%H_%M")
DEFAULT_IP_PATH = f'data/{now}/ips'
DEFAULT_ZMAP_PATH = f'data/{now}/results_encoded'
DEFAULT_DECODED_PATH = f'data/{now}/results_decoded'

