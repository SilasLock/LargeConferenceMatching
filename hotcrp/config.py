
##
## used by hotcrp_to_lcm.py
##


HOTCRP_PCINFO_CSV = "ec2023-pcinfo.csv"     # export from hotcrp
HOTCRP_DATA_JSON = "ec2023-data.json"       # export from hotcrp
HOTCRP_ALLPREFS_CSV = "ec2023-allprefs.csv" # export from hotcrp

REVIEWER_EXPERIENCE_CSV = "reviewer-experience.csv" # homespun PC and publication history.
                                                    # last,first,pc_count,paper_count,email 

SS_SCORES_CSV = "semantic-scholar-scores.csv"  # from semantic scholar peer-review peer-match
SS_CONFLICTS_CSV = "semantic-scholar-cois.csv" # from semantic scholar peer-review conflict-of-interest
ACL_SCORES_CSV = "acl-scores.csv"              # homespum ACM similarity scores

AC_TAG = "ac"
PC_TAG = "programcommittee"

LCM_CONFLICTS_CSV = "conflicts.csv"           #
LCM_REVIEWER_PROPS_CSV = "reviewer-props.csv" # 
LCM_BIDS_CSV = "reviewer-bids.csv"            # paper, reviewer, bid
LCM_RAW_SCORES_CSV = "raw-scores.csv"


##
## used by
##   - replace_emails_with_numbers.py
##   - replace_numbers_with_emails.py
##


input_name = "results/test_iter_0_matching.csv"
output_name = "results/final_matching.csv"
conversion_dict_name = "conversion_dicts/id_to_email.pkl"

input_folder = "data_pre_conversion/"
output_folder = "data/"

raw_scores_file_name = "raw-scores.csv"
bids_file_name = "bids-hotcrp.csv"
reviewers_file_name = "reviewers_file.csv"
coauthor_distance_file_name = "coauthor_distance_file.csv"
ID_TO_EMAIL_JSON =  "id_to_email.json"


