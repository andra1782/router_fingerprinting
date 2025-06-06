# IP Country Extraction from Traceroute

Set of scripts allowing the extraction of IPs (hops excluding the first one) from a [traceroute file](https://data-store.ripe.net/datasets/atlas-daily-dumps/). Specifically made to work with the RIPE Atlas Daily Dumps Index.

## Requirements:
  - Python
  - [geoip2](https://pypi.org/project/geoip2/)
  - [GeoLite2-Country database](https://dev.maxmind.com/geoip/docs/databases/city-and-country/)
  - [GeoLite2-City database](https://dev.maxmind.com/geoip/docs/databases/city-and-country/)
  - [GeoLite2-ASN database](https://dev.maxmind.com/geoip/docs/databases/asn/)
  

Note: The GeoLite2 databases used must be **Country**, **City**, and **ASN** databases. Place your database files in the `databases` folder. The scripts will automatically look for them there.

## Simplified version

For all the IPs from a single day only through a link, i.e. [the 11th of May](https://data-store.ripe.net/datasets/atlas-daily-dumps/2025-05-11/):

```
python pipeline.py --url https://data-store.ripe.net/datasets/atlas-daily-dumps/{day} <country_db> <city_db> <asn_db>
```
- `<country_db>`: Your GeoIP2 country database file (e.g., `GeoLite2-Country.mmdb`)
- `<city_db>`: Your GeoIP2 city database file (e.g., `GeoLite2-City.mmdb`)
- `<asn_db>`: Your GeoIP2 ASN database file (e.g., `GeoLite2-ASN.mmdb`)

For all the IPs from a set of custom links, each pointing to a .bz2 archive, add them to a file, with each of them on a separate line, then:

```
python pipeline.py --url_file <url-file-name> <country_db> <city_db> <asn_db>
```
- `<country_db>`: Your GeoIP2 country database file
- `<city_db>`: Your GeoIP2 city database file
- `<asn_db>`: Your GeoIP2 ASN database file
- `<url-file-name>`: Name of file with links to .bz2 archives

**The results can be found in `data/{run}/results/{filters}_results.txt`.** You may inspect the rest of `data/{run}` for the list of all unique IPs, their respective countries, cities, autonomous system numbers and autonomous system organizations. There is a separate file for each archive included. 

`{run}` is normally determined by the local date/time of when the script was executed. 

**Optional arguments**:
- `--run-name <name>`: Specify a custom name for the run directory within `/data`. Setting this to the name of an already used run directory may allow re-using extracted archives.
- `--keep-temp`: Does not remove downloads and extracted archives. **WARNING**: On average, a download is 2GB and an extracted archive is 25GB. **Use with caution**.
- `--country "<country-name>"`: Filter by a specific country, by default "The Netherlands" is used. Note: The country name *must* be enclosed in quotes ("").
- `--city "<city-name>"`: Filter by a specific city. Note: The city name *must* be enclosed in quotes ("").
- `--asn "<asn>"`: Filter by a specific ASN.
- `--org "<organization>"`: Filter by a specific organization name. Note: The organization name *must* be enclosed in quotes ("").
- `--skip-extraction`: Skip download, extraction and IP extraction steps (use existing IP files). Useful when re-running with different filters or continuing from a previous run.

You can use any combination of these filter options. For example:
```bash
python pipeline.py --url_file archive_links.txt GeoLite2-Country.mmdb GeoLite2-City.mmdb GeoLite2-ASN.mmdb --country "The Netherlands" --city "Delft"
```

The output files will be named based on the filters applied. For example:
- `{base_name}_ips_country_netherlands.txt` for country filter
- `{base_name}_ips_country_netherlands_city_amsterdam.txt` for country and city filters
- `{base_name}_ips_country_netherlands_city_amsterdam_asn_12345.txt` for country, city, and ASN filters

## Other notes:

Modifying / renaming the contents of `/data/{run}/filtered_ips/` specifically may lead to different results as all of the files within each filter directory are used to compute the final set of IPs for that filter combination.

## Individual scripts:

To extract all the IPs from the traceroute:

```
python extract-ips.py <path-to-traceroute-file>
```

To find the country, city, ASN and organization for each IP address:

```
python extract-details.py <ip-file> <output-file> <country_db> <city_db> <asn_db>
```
- `<ip-file>`: File containing the IP addresses (either from the previous extraction or any other source)
- `<output-file>`: File where results will be saved, formatted as `{IP, Country, City, ASN, Organization}`
- `<country_db>`: Your GeoIP2 country database file
- `<city_db>`: Your GeoIP2 city database file
- `<asn_db>`: Your GeoIP2 ASN database file

To filter the results by country, city, ASN, or organization:

```
python filters.py <ip-with-details-file> [--country <country-name>] [--city <city-name>] [--asn <asn>] [--org <organization>] [--output_file <output-file-name>]
```

- `<ip-with-details-file>`: File with IP addresses and their corresponding details (CSV format: ip,country,city,asn,organization)
- `--country <country-name>`: (Optional) Country to filter by (e.g., "The Netherlands")
- `--city <city-name>`: (Optional) City to filter by
- `--asn <asn>`: (Optional) ASN to filter by
- `--org <organization>`: (Optional) Organization name to filter by
- `--output_file <output-file-name>`: (Optional) File to save the filtered IPs. If not specified, a name will be generated based on the applied filters.

The output file will be named based on the filters applied. For example:
- `{base_name}_filtered_country_netherlands.txt` for country filter
- `{base_name}_filtered_city_amsterdam.txt` for city filter
- `{base_name}_filtered_asn_12345.txt` for ASN filter
- `{base_name}_filtered_org_company_name.txt` for organization filter
- Multiple filters will be combined in the filename (e.g., `{base_name}_filtered_country_netherlands_city_amsterdam.txt`)
