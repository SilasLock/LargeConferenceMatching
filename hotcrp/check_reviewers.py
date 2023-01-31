#!/usr/bin/env python3


from config import *
from util import *
from pprint import pprint

needs_files = [
    # LCM_CONFLICTS_CSV,
    LCM_REVIEWER_PROPS_CSV,
    LCM_BIDS_CSV,
    LCM_RAW_SCORES_CSV,
    LCM_COAUTHOR_DISTANCE_CSV
]

print(f"NEEDS {needs_files}")

print()

datas = [
    # conflicts_data,
    reviewers_data,
    bids_data,
    scores_data,
    distances_data
] = [read_csv(DATA_WITH_EMAILS_FOLDER + f) for f in needs_files]

ids = [
    # conflicts_ids,
    reviewers_ids,
    bids_ids,
    scores_ids
] = [{r['reviewer'] for r in data} for data in datas[:-1]]

ids += [
    {r[f'reviewer_{i}'] for r in distances_data for i in [1,2]}
]



if len(reviewers_ids) != len(reviewers_data):
    print(f"failed check: {LCM_REVIEWER_PROPS_CSV} contains duplicate reviewers [{len(reviewers_ids)} != {len(reviewers_data)}]")

for (f,i) in zip(needs_files,ids):

    diff = i - reviewers_ids

    if diff:
        print(f"failed check: unknown reviewers in [{f}]:")
        pprint(diff)

