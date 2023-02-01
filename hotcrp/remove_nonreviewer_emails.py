import csv
import pandas as pd
from config import *


# DATA_WITH_NONREVIEWERS = "."
# DATA_WITH_EMAILS_FOLDER = "data"

# LCM_RAW_SCORES_CSV = "raw-scores.csv"
# LCM_BIDS_CSV = "bids-hotcrp.csv"
# LCM_REVIEWER_PROPS_CSV = "reviewers_file.csv"
# LCM_COAUTHOR_DISTANCE_CSV = "coauthor_distance_file.csv"

reviewer_emails = set()

with open(DATA_WITH_NONREVIEWERS + LCM_REVIEWER_PROPS_CSV, mode="r") as reviewers_file:
    reviewers_file_rows = csv.DictReader(reviewers_file)
    for row in reviewers_file_rows:
        reviewer_emails.add(row["reviewer"])

raw_scores_file = pd.read_csv(DATA_WITH_NONREVIEWERS + LCM_RAW_SCORES_CSV)
raw_scores_file = raw_scores_file[(raw_scores_file["reviewer"].isin(reviewer_emails))]
raw_scores_file.to_csv(DATA_WITH_EMAILS_FOLDER + LCM_RAW_SCORES_CSV, index=False)

bids_file = pd.read_csv(DATA_WITH_NONREVIEWERS + LCM_BIDS_CSV)
bids_file = bids_file[(bids_file["reviewer"].isin(reviewer_emails))]
bids_file.to_csv(DATA_WITH_EMAILS_FOLDER + LCM_BIDS_CSV, index=False)

coauthor_distance_file = pd.read_csv(DATA_WITH_NONREVIEWERS + LCM_COAUTHOR_DISTANCE_CSV)
coauthor_distance_file = coauthor_distance_file[(coauthor_distance_file["reviewer_1"].isin(reviewer_emails))]
coauthor_distance_file = coauthor_distance_file[(coauthor_distance_file["reviewer_2"].isin(reviewer_emails))]
coauthor_distance_file.to_csv(DATA_WITH_EMAILS_FOLDER + LCM_COAUTHOR_DISTANCE_CSV, index=False)

# Just copy over the reviewers file to the new directory without doing anything.
reviewers_file = pd.read_csv(DATA_WITH_NONREVIEWERS + LCM_REVIEWER_PROPS_CSV)
reviewers_file.to_csv(DATA_WITH_EMAILS_FOLDER + LCM_REVIEWER_PROPS_CSV, index=False)
