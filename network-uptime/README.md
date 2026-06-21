Network Uptime Data
This folder contains the raw and cleaned network uptime data along with the Python script used to process it.

Files
CDMS_raw_anonymized.csv — Raw monthly network monitoring export, anonymized. Contains daily uptime and downtime status per base station in a wide calendar grid format covering April through December 2025.
bts_april_uptime_summary_anonymized.csv — Cleaned output showing total downtime minutes and uptime percentage per base station for April 2025, provided as a representative sample. The same script was applied across all months individually to validate accuracy before results were combined.
bts_uptime_reshape.py — Python script used to reshape the raw wide-format grid into a tidy long-format table and calculate uptime percentages per base station. The TDT column was used as the source of truth for downtime duration. The denominator for uptime calculation is based on days actually present in the data rather than a fixed calendar assumption.

Note on Data
All base station names have been replaced with anonymized placeholders and the company name replaced with a pseudonym to protect proprietary information.
