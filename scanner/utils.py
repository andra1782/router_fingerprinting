class Singleton(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


def hex_to_text2pcap_format(hex_data: str) -> str:
    lines = []
    hex_bytes = [hex_data[i : i + 2] for i in range(0, len(hex_data), 2)]
    for i in range(0, len(hex_bytes), 16):
        line_bytes = hex_bytes[i : i + 16]
        line = f'{i:04x}  {" ".join(line_bytes)}'
        lines.append(line)
    return '\n'.join(lines)


def seconds_to_uptime(seconds: str) -> str:
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f'{days}d{hours}h{minutes}m{secs}s'
