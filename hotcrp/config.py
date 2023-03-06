
##
## used by hotcrp_to_lcm.py
##

COMMITTEE_AUX_CSV = "committee.csv"

HOTCRP_EMAIL_ALIASES_CSV = "email-aliases.csv"

HOTCRP_PCINFO_CSV = "ec2023-pcinfo.csv"     # export from hotcrp
HOTCRP_DATA_JSON = "ec2023-data.json"       # export from hotcrp
HOTCRP_ALLPREFS_CSV = "ec2023-allprefs.csv" # export from hotcrp
HOTCRP_PCASSIGNMENT_CSV = "ec2023-pcassignments.csv" # export from hotcrp

REVIEWER_EXPERIENCE_CSV = "reviewer-experience.csv" # homespun PC and publication history.
                                                    # last,first,pc_count,paper_count,email 

SS_SCORES_CSV = "semantic-scholar-scores.csv"  # from semantic scholar peer-review peer-match
SS_CONFLICTS_CSV = "semantic-scholar-cois.csv" # from semantic scholar peer-review conflict-of-interest
ACL_SCORES_CSV = "acl-scores.csv"              # homespum ACM similarity scores
DBLP_CONFLICTS_CSV = "dblp-conflicts.csv"

TC_SCORES_RAW_CSV = "tc-scores-raw.csv"
TC_SCORES_CSV = "tc-scores.csv"

AC_TAG = "ac"
PC_TAG = "programcommittee"

LCM_CONFLICTS_CSV = "conflicts.csv"           #

LCM_REVIEWER_PROPS_CSV = "reviewers.csv" # 
LCM_BIDS_CSV = "bids.csv"            # paper, reviewer, bid
LCM_RAW_SCORES_CSV = "scores.csv"
LCM_COAUTHOR_DISTANCE_CSV = "distances.csv"
LCM_FIXED_SOLUTION_CSV = "fixed-solution.csv"


##
## used by
##   - replace_emails_with_numbers.py
##   - replace_numbers_with_emails.py
##


input_name = "results/test_iter_0_matching.csv"
output_name = "results/final_matching.csv"
conversion_dict_name = "conversion_dicts/id_to_email.pkl"

DATA_WITH_NONREVIEWERS = "data_with_nonreviewers/"
DATA_WITH_EMAILS_FOLDER = "data_with_emails/"
DATA_FOLDER = "data/"

# raw_scores_file_name = "raw-scores.csv"
# bids_file_name = "bids-hotcrp.csv"
# reviewers_file_name = "reviewers_file.csv"

COAUTHOR_DISTANCE_FILE_NAME = "coauthor_distance_file.csv"
EMAIL_TO_ID_JSON = "email_to_id.json"
ID_TO_EMAIL_JSON =  "id_to_email.json"
