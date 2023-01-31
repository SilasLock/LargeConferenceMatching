import csv
import pandas as pd
import pickle

# input_name should be the matching file, double check to make sure the name is right.
input_name = "results/test_iter_0_matching.csv"
output_name = "results/final_matching.csv"
conversion_dict_name = "conversion_dicts/id_to_email.pkl"

# Load the id_to_email dictionary into this program.
with open(conversion_dict_name, "rb") as handle:
    id_to_email = pickle.load(handle)

def id_to_email_func(x):
    return id_to_email[x]

print(id_to_email)

# `_matching.csv` - Main output file containing the complete matching. Columns are `paper,reviewer,role,score,seniority`.
# ^^ From the readme file of the LargeConferenceMatching repository.
matching_file = pd.read_csv(input_name)
matching_file["reviewer"] = matching_file["reviewer"].transform(id_to_email_func)
matching_file.to_csv(output_name, index=False)
