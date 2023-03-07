#!/usr/bin/env python3

import util
from config import *
import sys

if len(sys.argv) not in [2,3]:
    print(f"USAGE: {sys.argv[0]} <results-file.csv> [<results-file-with-emails.csv>]")
    exit(-1)

results_csv = sys.argv[1]

results_output_csv = sys.argv[2] if len(sys.argv) == 3 else results_csv.replace(".csv","_withemails.csv")

assignment_output_csv = results_csv.replace(".csv","_assignment.csv")



try:
    email_aliases = dict([(ea['alias'].lower(),ea['email'].lower()) for ea in util.read_csv(HOTCRP_EMAIL_ALIASES_CSV)])
except:
    print(f"failed to read email alias file [{HOTCRP_EMAIL_ALIASES_CSV}]")
    email_aliases = {}

def email(e):
    e = e.lower()
    return email_aliases.get(e,e)




results_data = util.read_csv(results_csv)

reviewers_data = util.read_csv(DATA_WITH_NONREVIEWERS + LCM_REVIEWER_PROPS_CSV)

conflicts_data = util.read_csv(DATA_WITH_NONREVIEWERS + LCM_CONFLICTS_CSV)
conflicts = {(c['paper'],email(c['reviewer_email'])) for c in conflicts_data}

def intzero(intstr):
    if not intstr:
        return 0
    else:
        return int(intstr)



pc_allprefs = util.read_csv(HOTCRP_ALLPREFS_CSV)
pcts = {(pc['paper'],email(pc['email'])):intzero(pc['topic_score']) for pc in pc_allprefs }
pcb = {(pc['paper'],email(pc['email'])):intzero(pc['preference']) for pc in pc_allprefs }

match_bid = {}
match_ts = {}
rev = {}
pap = {}

def getzero(lookup,key):
    if key not in lookup:
        return 0
    else:
        return lookup[key]

ids_to_email = {r['reviewer']:r['reviewer_email'] for r in reviewers_data}
email_to_role = {r['reviewer_email']:r['role'] for r in reviewers_data}

conflict_rows = []
for r in results_data:
    reviewer = ids_to_email.get(r['reviewer'],'')
    paper = r['paper']
    
    r['reviewer_email'] = reviewer

    match = (paper,reviewer)

    if match in conflicts:
        conflict_rows += [r]
        print(f"CONFLICT on paper {r['paper']} with reviewer {r['reviewer_email']}")

    ts = getzero(pcts,match)
    bid = getzero(pcb,match)

    if ts not in match_ts:
        match_ts[ts] = 0
    if bid not in match_bid:
        match_bid[bid] = 0

    match_bid[bid] += 1
    match_ts[ts] += 1

    score = round(float(r['score']),1)

    if reviewer not in rev:
        rev[reviewer] = {'bids':[],'topic_scores':[],'papers':[],'scores':[]}

    rev[reviewer]['bids'] += [bid]
    rev[reviewer]['topic_scores'] += [ts]
    rev[reviewer]['papers'] += [int(paper)]
    rev[reviewer]['scores'] += [score]
    
    if paper not in pap:
        pap[paper] = {'bids':[],'topic_scores':[],'reviewers':[],'scores':[]}

    pap[paper]['bids'] += [bid]
    pap[paper]['topic_scores'] += [ts]
    pap[paper]['reviewers'] += [reviewer]
    pap[paper]['scores'] += [score]
        

    
    
    

util.write_csv(results_output_csv,results_data)

print()
print("AGGREGATE ANALYSIS")
print()

print(f"conflict summary: {len(conflict_rows)} conflicts.")

print()

print("topic match summary:")

for k in sorted(match_ts.keys()):
    print(f"  {k}: {match_ts[k]}")

print()

print("bid match summary:")

for k in sorted(match_bid.keys()):
    print(f"  {k}: {match_bid[k]}")

statkeys = ['bids','topic_scores','scores','reviewers','papers']

def lststr(lst):
    return ", ".join([f"{s:4}" for s in lst])

print()
print("UNHAPPY PC ANALYSIS")
print()



for r in rev.keys():
    sbids = sorted(rev[r]['bids'])

    if sbids[2] <= 0:
        print(f"  * three bad bids for [{r}]")
        for k in statkeys:
            if k in rev[r]:
                print(f"\t{k:10.10}: {lststr(rev[r][k])}")

        print()

    elif sbids[1] <= 0:
        print(f"  - two bad bids for [{r}]")
        for k in statkeys:
            if k in rev[r]:
                print(f"\t{k:10.10}: {lststr(rev[r][k])}")

        print()
    
print()
print("UNHAPPY PAPER ANALYSIS")
print()


unhappy_papers = set()
need_reviewers = set()

for p in pap.keys():
    sbids = sorted(pap[p]['bids'])

    
    if len(sbids) != 3:
        print(f"  - needs reviewers for paper [{p}]")
        for k in statkeys:
            if k in pap[p]:
                print(f"\t{k:10.10}: {lststr(pap[p][k])}")
        print()
        need_reviewers.add(int(p))
        
    elif sbids[1] <= 0:
        print(f"  * two bad bids for paper [{p}]")
        for k in statkeys:
            if k in pap[p]:
                print(f"\t{k:10.10}: {lststr(pap[p][k])}")
        print()
        unhappy_papers.add(int(p))


print(f"ALL UNHAPPY PAPERS: {unhappy_papers}")
print(f"NEED REVIEWERS PAPERS: {need_reviewers}")


computer_scientist_ids = {int(r["reviewer"]) for r in reviewers_data if (1 == r["computer_scientist"])}
matched_paper_count = len({int(r["paper"]) for r in results_data})
good = {int(r["paper"]) for r in results_data if int(r["reviewer"]) in computer_scientist_ids}
print("We want all " + str(matched_paper_count) + " papers (the number being reviewed) to each have at least one computer scientist reviewing them.")
print("Total papers reviewed = " + str(matched_paper_count))
print("Total papers reviewed by at least 1 computer scientist = " + str(len(good)))
if (matched_paper_count == len(good)):
    print("\tThese are the same value! Good work.")
else:
    print("\tWARNING! These are not the same value! That means there's probably some paper being reviewed by no one with CS expertise!")



assignment = [
    {
        'paper':r['paper'],
        'action':"review",
        'email':r['reviewer_email'],
        'reviewtype':'primary' if r['role'] == "PC" else 'meta',
        'round': 'round1' if r['role'] == "PC" else 'final'
    }
    for r in results_data
]

util.write_csv(assignment_output_csv,assignment)

