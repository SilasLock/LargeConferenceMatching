#!/usr/bin/env python3

import util
from config import *
import sys

if len(sys.argv) not in [2,3]:
    print(f"USAGE: {sys.argv[0]} <results-file.csv> [<results-file-with-emails.csv>]")
    exit(-1)

results_csv = sys.argv[1]

results_output_csv = sys.argv[2] if len(sys.argv) == 3 else results_csv.replace(".csv","_out.csv")

results_data = util.read_csv(results_csv)

reviewers_data = util.read_csv(DATA_WITH_NONREVIEWERS + LCM_REVIEWER_PROPS_CSV)

ids_to_email = {r['reviewer']:r['reviewer_email'] for r in reviewers_data}

for r in results_data:
    r['reviewer_email'] = ids_to_email.get(r['reviewer'],'')

util.write_csv(results_output_csv,results_data)



