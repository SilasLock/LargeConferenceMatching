#!/usr/bin/env python3

import csv
import pandas as pd
import util

from config import *

reviewer_emails = set()

with open(input_folder + raw_scores_file_name, mode="r") as raw_scores_file:
    raw_scores_file_rows = csv.DictReader(raw_scores_file)
    for row in raw_scores_file_rows:
        reviewer_emails.add(row["reviewer"])

with open(input_folder + bids_file_name, mode="r") as bids_file:
    bids_file_rows = csv.DictReader(bids_file)
    for row in bids_file_rows:
        reviewer_emails.add(row["reviewer"])

with open(input_folder + reviewers_file_name, mode="r") as reviewers_file:
    reviewers_file_rows = csv.DictReader(reviewers_file)
    for row in reviewers_file_rows:
        reviewer_emails.add(row["reviewer"])

with open(input_folder + coauthor_distance_file_name, mode="r") as coauthor_distance_file:
    coauthor_distance_file_rows = csv.DictReader(coauthor_distance_file)
    for row in coauthor_distance_file_rows:
        reviewer_emails.add(row["reviewer_1"])
        reviewer_emails.add(row["reviewer_2"])

print("Finished locating all reviewer emails.")

ordered_emails = sorted(list(reviewer_emails))
email_to_id = dict()
id_to_email = dict()

for i in range(0, len(ordered_emails)):
    email_to_id[ordered_emails[i]] = i
    id_to_email[i] = ordered_emails[i]

print("Constructed a dictionary from emails to integer IDs.")

def email_to_id_func(x):
    return email_to_id[x]

raw_scores_file = pd.read_csv(input_folder + raw_scores_file_name)
raw_scores_file["reviewer"] = raw_scores_file["reviewer"].transform(email_to_id_func)
raw_scores_file.to_csv(output_folder  + raw_scores_file_name, index=False)

bids_file = pd.read_csv(input_folder  + bids_file_name)
bids_file["reviewer"] = bids_file["reviewer"].transform(email_to_id_func)
bids_file.to_csv(output_folder  + bids_file_name, index=False)

reviewers_file = pd.read_csv(input_folder  + reviewers_file_name)
reviewers_file["reviewer"] = reviewers_file["reviewer"].transform(email_to_id_func)
reviewers_file.to_csv(output_folder  + reviewers_file_name, index=False)

coauthor_distance_file = pd.read_csv(input_folder + coauthor_distance_file_name)
coauthor_distance_file["reviewer_1"] = coauthor_distance_file["reviewer_1"].transform(email_to_id_func)
coauthor_distance_file["reviewer_2"] = coauthor_distance_file["reviewer_2"].transform(email_to_id_func)
coauthor_distance_file.to_csv(output_folder  + coauthor_distance_file_name, index=False)

print("Converted all reviewer emails into (integer) IDs.")

with open(output_folder + "email_to_id.pkl", "wb") as handle:
    pickle.dump(email_to_id, handle, protocol=pickle.HIGHEST_PROTOCOL)

    
util.write_json(output_folder  + ID_TO_EMAIL_JSON, id_to_email)


# Uncomment this if you ever want to load the email_to_id dictionary into a program again.
# with open(output_folder  + "email_to_id.pkl", "rb") as handle:
#     same_as_email_to_dict = pickle.load(handle)

print("Saved email-to-ID dictionary as a .pkl file, as well as the reverse mapping.")

print("New files placed into the " + output_folder + " directory.")
