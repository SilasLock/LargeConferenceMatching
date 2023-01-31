#!/usr/bin/env python3

import csv
import pandas as pd
import util


# input_name should be the matching file, double check to make sure the name is right.

id_to_email = util.read_json(conversion_dict_name)

def id_to_email_func(x):
    return id_to_email[x]

print(id_to_email)

# `_matching.csv` - Main output file containing the complete matching. Columns are `paper,reviewer,role,score,seniority`.
# ^^ From the readme file of the LargeConferenceMatching repository.
matching_file = pd.read_csv(input_name)
matching_file["reviewer"] = matching_file["reviewer"].transform(id_to_email_func)
matching_file.to_csv(output_name, index=False)
