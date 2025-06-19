import pandas as pd
import matplotlib.pyplot as plt
import re
import sys
import argparse
from datetime import datetime, timedelta
import os

def parse_engine_time(time_str):
    if pd.isna(time_str) or isinstance(time_str, float):
        return None
    if time_str == '0d0h0m0s':
        return timedelta(seconds=0)
    match = re.match(r'(\d+)d(\d+)h(\d+)m(\d+)s', str(time_str))
    if match:
        days, hours, minutes, seconds = map(int, match.groups())
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return None

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze router reboot data during outage period')
    parser.add_argument('input_file', help='Path to the input CSV file')
    parser.add_argument('--output', '-o', default='plots/outage_reboots.png',
                       help='Output file path for the plot (default: outage_reboots.png)')
    parser.add_argument('--collection-time', default='2025-06-16 15:00:00',
                       help='Collection time in format YYYY-MM-DD HH:MM:SS (default: 2025-06-16 15:00:00)')
    parser.add_argument('--outage-start', default='2025-04-28 12:00:00',
                       help='Outage start time in format YYYY-MM-DD HH:MM:SS (default: 2025-04-28 12:00:00)')
    parser.add_argument('--outage-end', default='2025-04-29 23:59:59',
                       help='Outage end time in format YYYY-MM-DD HH:MM:SS (default: 2025-04-29 23:59:59)')
    return parser.parse_args()


args = parse_arguments()

try:
    df = pd.read_csv(args.input_file)
    df['uptime'] = df['snmpEngineTime'].apply(parse_engine_time)
    
    collection_time = datetime.strptime(args.collection_time, '%Y-%m-%d %H:%M:%S')
    df['reboot_time'] = collection_time - df['uptime']
    
    outage_start = datetime.strptime(args.outage_start, '%Y-%m-%d %H:%M:%S')
    outage_end = datetime.strptime(args.outage_end, '%Y-%m-%d %H:%M:%S')
    
    def plot_ip_reboots(df, outage_start, outage_end, output_path):
        rebooted_during_outage = df[(df['reboot_time'] >= outage_start) & (df['reboot_time'] <= outage_end)].copy()
        print(f"Total IP addresses: {len(df)}")
        print(f"IP addresses rebooted during outage: {len(rebooted_during_outage)}")
        if not rebooted_during_outage.empty:
            plt.figure(figsize=(12, 6))
            rebooted_during_outage.loc[:, 'reboot_hour'] = rebooted_during_outage['reboot_time'].dt.floor('h')
            hourly_counts = rebooted_during_outage['reboot_hour'].value_counts().sort_index()
            full_range = pd.date_range(start=outage_start, end=outage_end, freq='h')
            hourly_counts = hourly_counts.reindex(full_range, fill_value=0)
            ax = hourly_counts.plot(kind='bar', color='salmon')
            plt.title('Reboots During Outage Period (from EngineTime)')
            plt.xlabel('Hour of Reboot')
            plt.ylabel('Number of IPs Rebooted')
            ax.set_xticklabels([pd.to_datetime(str(x)).strftime('%H:%M') for x in hourly_counts.index])
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            print(f"IP plot saved as '{output_path}'")

    def plot_router_reboots(df, outage_start, outage_end, output_path):
        routers = df.dropna(subset=['engineIDData']).groupby('engineIDData').first().reset_index()
        print(f"Total unique routers (by engineIDData): {len(routers)}")
        routers['reboot_time'] = df.dropna(subset=['engineIDData']).groupby('engineIDData')['reboot_time'].min().values
        routers_rebooted = routers[(routers['reboot_time'] >= outage_start) & (routers['reboot_time'] <= outage_end)].copy()
        print(f"Routers rebooted during outage: {len(routers_rebooted)}")
        if not routers_rebooted.empty:
            plt.figure(figsize=(12, 6))
            routers_rebooted.loc[:, 'reboot_hour'] = routers_rebooted['reboot_time'].dt.floor('h')
            router_hourly_counts = routers_rebooted['reboot_hour'].value_counts().sort_index()
            full_range = pd.date_range(start=outage_start, end=outage_end, freq='h')
            router_hourly_counts = router_hourly_counts.reindex(full_range, fill_value=0)
            ax2 = router_hourly_counts.plot(kind='bar', color='skyblue')
            plt.title('Router Reboots During Outage Period (from EngineTime, unique EngineIds)')
            plt.xlabel('Hour of Reboot')
            plt.ylabel('Number of Routers Rebooted')
            ax2.set_xticklabels([pd.to_datetime(str(x)).strftime('%H:%M') for x in router_hourly_counts.index])
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            print(f"Router plot saved as '{output_path}'")

    output_dir = os.path.dirname(args.output) or '.'
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(args.output))[0]
    ip_plot_path = os.path.join(output_dir, f"{base_name}_ips.png")
    router_plot_path = os.path.join(output_dir, f"{base_name}_routers.png")

    plot_ip_reboots(df, outage_start, outage_end, ip_plot_path)
    plot_router_reboots(df, outage_start, outage_end, router_plot_path)
    
except Exception as e:
    print(f"Error occurred: {str(e)}", file=sys.stderr)
    sys.exit(1)
