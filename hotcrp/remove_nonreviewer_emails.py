import csv
import pandas as pd

input_folder = "data_pre_conversion"
output_folder = "data_mid_conversion"

raw_scores_file_name = "raw-scores.csv"
bids_file_name = "bids-hotcrp.csv"
reviewers_file_name = "reviewers_file.csv"
coauthor_distance_file_name = "coauthor_distance_file.csv"

reviewer_emails = set()

with open(input_folder + "/" + reviewers_file_name, mode="r") as reviewers_file:
    reviewers_file_rows = csv.DictReader(reviewers_file)
    for row in reviewers_file_rows:
        reviewer_emails.add(row["reviewer"])

raw_scores_file = pd.read_csv(input_folder + "/" + raw_scores_file_name)
raw_scores_file = raw_scores_file[(raw_scores_file["reviewer"].isin(reviewer_emails))]
raw_scores_file.to_csv(output_folder + "/" + raw_scores_file_name, index=False)

bids_file = pd.read_csv(input_folder + "/" + bids_file_name)
bids_file = bids_file[(bids_file["reviewer"].isin(reviewer_emails))]
bids_file.to_csv(output_folder + "/" + bids_file_name, index=False)

coauthor_distance_file = pd.read_csv(input_folder + "/" + coauthor_distance_file_name)
coauthor_distance_file = coauthor_distance_file[(coauthor_distance_file["reviewer_1"].isin(reviewer_emails))]
coauthor_distance_file = coauthor_distance_file[(coauthor_distance_file["reviewer_2"].isin(reviewer_emails))]
coauthor_distance_file.to_csv(output_folder + "/" + coauthor_distance_file_name, index=False)
