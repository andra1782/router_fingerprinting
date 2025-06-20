import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import csv
import argparse
from io import StringIO

def load_txt_files(txt_dir):
    """Load all TXT files from the specified directory using a more robust CSV reader"""
    txt_files = glob.glob(os.path.join(txt_dir, '*.txt'))
    if not txt_files:
        raise FileNotFoundError(f"No TXT files found in directory: {txt_dir}")
    
    dfs = []
    for file in txt_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            reader = csv.reader(StringIO(content), delimiter=',', quotechar='"')
            
            processed_rows = []
            for row in reader:
                if len(row) < 5:
                    row += [''] * (5 - len(row))
                elif len(row) > 5:
                    row = row[:4] + [','.join(row[4:])]
                processed_rows.append(row)
            
            df = pd.DataFrame(processed_rows, columns=['ip', 'country', 'city', 'asn', 'asn_name'])
            dfs.append(df)
            
        except Exception as e:
            print(f"Error processing file {os.path.basename(file)}: {str(e)}")
            continue
    
    if not dfs:
        raise ValueError("No valid TXT files could be loaded")
    
    return pd.concat(dfs, ignore_index=True)

def analyze_data(csv_file, txt_df):
    csv_df = pd.read_csv(csv_file)
    
    txt_df['country'] = txt_df['country'].str.strip()
    csv_df['country'] = csv_df['country'].str.strip()
    
    txt_df = txt_df[txt_df['country'] != 'Unknown']
    csv_df = csv_df[csv_df['country'] != 'Unknown']
    
    txt_ip_count = txt_df.groupby('country')['ip'].nunique().sort_values(ascending=False)
    
    common_ips = set(txt_df['ip']).intersection(set(csv_df['ip']))
    txt_df['in_csv'] = txt_df['ip'].isin(common_ips)
    txt_ip_in_csv = txt_df[txt_df['in_csv']].groupby('country')['ip'].nunique().sort_values(ascending=False)
    
    engine_id_count = csv_df.groupby('country')['engineIDData'].nunique().sort_values(ascending=False)
    engine_ip_counts = csv_df.groupby(['country', 'engineIDData'])['ip'].count()
    max_ips_per_engine = engine_ip_counts.groupby('country').max().sort_values(ascending=False)
    
    return {
        'txt_ip_count': txt_ip_count,
        'txt_ip_in_csv': txt_ip_in_csv,
        'engine_id_count': engine_id_count,
        'max_ips_per_engine': max_ips_per_engine,
        'common_ips_count': len(common_ips)
    }

def plot_results(results, output_dir='plots'):
    """Generate plots from the analysis results"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    plt.figure(figsize=(18, 9))

    # Get the top 20 countries by ip count
    top_countries = results['txt_ip_count'].head(20).index

    x = range(len(top_countries))
    width = 0.35

    response_rates = (results['txt_ip_in_csv'][top_countries] / results['txt_ip_count'][top_countries]) * 100

    plt.title('IP Discovery vs SNMPv3 Response Rates by Country', fontsize=16, pad=20)
    plt.ylabel('Number of IPs', fontsize=12)
    plt.xlabel('Country', fontsize=12)
    plt.xticks(x, top_countries, rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(fontsize=12, loc='upper right')

    for i in x:
        plt.text(i - width/2, results['txt_ip_count'][top_countries[i]] + 5, 
                f"{results['txt_ip_count'][top_countries[i]]:,}", 
                ha='center', va='bottom', fontsize=9)
        
        plt.text(i + width/2, results['txt_ip_in_csv'][top_countries[i]] + 5, 
                f"{results['txt_ip_in_csv'][top_countries[i]]:,}", 
                ha='center', va='bottom', fontsize=9)
        
        mid_point = (results['txt_ip_count'][top_countries[i]] + results['txt_ip_in_csv'][top_countries[i]]) / 2
        plt.text(i, mid_point, 
                f"{response_rates.iloc[i]:.1f}%", 
                ha='center', va='center', fontsize=9, fontweight='bold',
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/merged_ip_comparison_with_percentages.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Plot: Engine IDs per country
    plt.figure(figsize=(14, 7))
    results['engine_id_count'].head(20).plot(kind='bar', color='salmon')
    plt.title('Top 20 Countries by Unique Engine ID Count', fontsize=14)
    plt.ylabel('Number of Unique Engine IDs', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/engine_id_count.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Plot: Max IPs per engine ID per country
    plt.figure(figsize=(14, 7))
    results['max_ips_per_engine'].head(20).plot(kind='bar', color='gold')
    plt.title('Top 20 Countries by Max IPs per Engine ID', fontsize=14)
    plt.ylabel('Maximum IPs sharing same Engine ID', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/max_ips_per_engine.png', dpi=300, bbox_inches='tight')
    plt.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze router reboot data during outage period')
    parser.add_argument('csv_file', help='Path to the input CSV file (scanner results)')
    parser.add_argument('txt_dir', help='Path to the input directory containing TXT files (traceroute results)')
    parser.add_argument('--output-dir', '-o', default='plots',
                        help='Output directory for the plots (default: plots)')
    return parser.parse_args()


args = parse_arguments()

try:
    df = pd.read_csv(args.csv_file)
    txt_dir = args.txt_dir

    print("Loading TXT files...")
    txt_df = load_txt_files(txt_dir)
    
    print("Analyzing data...")
    results = analyze_data(args.csv_file, txt_df)
    
    print("Generating plots...")
    plot_results(results)
    
    print("\nAnalysis complete. Plots saved in 'plots' directory.")
    print("\n=== Summary Statistics ===")
    print(f"Total unique IPs in TXT files: {results['txt_ip_count'].sum():,}")
    print(f"Total unique countries in TXT files: {len(results['txt_ip_count'])}")
    print(f"Total TXT IPs also found in CSV: {results['common_ips_count']:,} ({results['common_ips_count']/results['txt_ip_count'].sum():.2%})")
    
    print("\nTop 5 Countries by IP count in TXT files:")
    for country, count in results['txt_ip_count'].head(5).items():
        print(f"  {country}: {count:,} IPs")
    
    print("\nTop 5 Countries by IPs in both files:")
    for country, count in results['txt_ip_in_csv'].head(5).items():
        print(f"  {country}: {count:,} IPs")
    
    print("\nTop 5 Countries by Engine ID count:")
    for country, count in results['engine_id_count'].head(5).items():
        print(f"  {country}: {count:,} Engine IDs")
    
    print("\nTop 5 Countries by Max IPs per Engine ID:")
    for country, count in results['max_ips_per_engine'].head(5).items():
        print(f"  {country}: {count:,} IPs sharing one Engine ID")

except Exception as e:
    print(f"\nError: {str(e)}")
    if isinstance(e, FileNotFoundError):
        print("Please check that:")
        print(f"1. The CSV file exists at: {os.path.abspath(args.csv_file)}")
        print(f"2. The TXT directory exists at: {os.path.abspath(txt_dir)}")
        print(f"3. The TXT directory contains .txt files")