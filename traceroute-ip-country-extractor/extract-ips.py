import json
import argparse
import os
import time 
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import islice

parser = argparse.ArgumentParser(description="Extract all IPs (dst_addr, src_addr, hops) from traceroute file")
parser.add_argument("file_name", help="Traceroute file")
parser.add_argument("--output_file", help="Output file")
parser.add_argument("num_lines", type=int, nargs="?", default=None, help="Number of lines to process (default: all)")
parser.add_argument(
    "--multithreading",
    nargs="?",
    const=4,  
    type=int,
    help="Multithreading; specify number of workers (optional, default: 4)"
)
args = parser.parse_args()

file_path = Path(args.file_name)


NUM_WORKERS = 4
if args.multithreading:
    NUM_WORKERS = args.multithreading
    
BATCH_SIZE = 25000

if not args.output_file:
    output_dir = file_path.parent.parent / "ips"  
    output_dir.mkdir(parents=True, exist_ok=True) 
    
    base_name = file_path.stem 
    
    args.output_file = output_dir / f"{base_name}_ips.txt"

ips = set()

def extract_ips(batch):
    lines_processed = 0 
        
    ips = set()
    for line in batch:
        try:
            entry = json.loads(line)
            first_hop = True
            for hop in entry.get('result', []):
                for hop_result in hop.get('result', []):
                    ip = hop_result.get('from')
                    if ip and first_hop:
                        first_hop = False
                        continue
                    if ip:
                        ips.add(ip)

            if not args.multithreading:
                lines_processed += 1
                if lines_processed % 5000 == 0:
                    print(f"\rProcessed {lines_processed} lines...", end="", flush=True)
        except json.JSONDecodeError:
            continue
    return ips

def make_batch(f, batch_size):
    while True:
        lines = list(islice(f, batch_size))
        if not lines:
            break
        yield lines


def multithreading_mode(f):
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = []
        lines_processed = 0
        
        ips = set()

        cnt = 1

        for batch in make_batch(f, BATCH_SIZE):
            if args.num_lines is not None and lines_processed >= args.num_lines:
                break

            futures.append(executor.submit(extract_ips, batch))
            lines_processed += len(batch)
            
            if cnt % 4 == 0:
                for future in futures:
                    ips.update(future.result())
                futures = []

            cnt += 1

            if lines_processed % 5000 == 0:
                print(f"\rProcessed {lines_processed} lines...", end="", flush=True)

        for future in futures:
            ips.update(future.result())

        return ips

def main():
    start_time = time.time()
    with open(file_path, "r") as f:    
        if args.multithreading:
            print(f"Multithreading enabled! Using {args.multithreading} workers.")
            ips = multithreading_mode(f)
        else:
            print(f"Running in single-threaded mode.")
            ips = extract_ips(f)

    dur = time.time() - start_time

    with open(args.output_file, "w") as output_file:
        for ip in sorted(ips):
            output_file.write(f"{ip}\n")
            
    print(f"\nProcessing complete. Extracted {len(ips)} unique IPs to {args.output_file}.")
    print(f"Total time taken: {dur:.2f} seconds")

if __name__ == "__main__":
    main()



