from pathlib import Path
import os 

CURR_DIR = Path(__file__).resolve().parent

ips = set()

for filename in os.listdir(CURR_DIR + "/filtered_results"):
   print(filename)
   with open((CURR_DIR / "/filtered_results" / filename), 'r') as f:
      for line in f:
         ips.add(line)

with open("results.txt", "w") as out:
   for ip in ips:
      out.write(ip)
