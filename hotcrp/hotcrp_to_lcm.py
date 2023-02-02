#!/usr/bin/env python3

from util import *

from config import *

write_csv_orig = write_csv
def write_csv(x, d):
    write_csv_orig(DATA_WITH_NONREVIEWERS + x, d)
    
## update PC preferences.
##    - create bids file <= (paper, reviewer, bid)
##    - create hotcrp conflicts file (paper, reviewer)
##    - create topic scores file (paper, reviewer, nk) <= nk is topic score.

try:
    email_aliases = dict([(ea['alias'].lower(),ea['email'].lower()) for ea in read_csv(HOTCRP_EMAIL_ALIASES_CSV)])
except:
    print(f"failed to read email alias file [{HOTCRP_EMAIL_ALIASES_CSV}]")
    email_aliases = {}


needs_files = [
    HOTCRP_PCINFO_CSV,
    HOTCRP_DATA_JSON,
    HOTCRP_ALLPREFS_CSV,
    REVIEWER_EXPERIENCE_CSV,
    SS_SCORES_CSV,
    SS_CONFLICTS_CSV,
    ACL_SCORES_CSV,
    DBLP_CONFLICTS_CSV,
    COAUTHOR_DISTANCE_FILE_NAME
]

creates_files = [
    LCM_CONFLICTS_CSV,
    LCM_REVIEWER_PROPS_CSV,
    LCM_BIDS_CSV,
    LCM_RAW_SCORES_CSV
]

print(f"NEEDS {needs_files}")
print(f"CREATES {creates_files}")
print()
print(f"WRITES TO {DATA_WITH_NONREVIEWERS}")
print()

# read pc data, parse tags as set, only keep pc and ac (remove track-chairs, etc)
pc_data = [
    {
        **pc,
        'tags':tags
    }
    for pc in read_csv(HOTCRP_PCINFO_CSV) 
    for tags in [{t for t in pc['tags'].split()}] 
    if AC_TAG in tags or PC_TAG in tags
]
print(f"read PC info [{HOTCRP_PCINFO_CSV}]")


# ids start from 1
id_to_email = dict(enumerate(sorted([pc['email'].lower() for pc in pc_data]),1))
email_to_id = dict([(e,i) for (i,e) in id_to_email.items()])


unknown_reviewer_emails = []

def id_for_email(email):
    global unknown_reviewer_emails

    email = email.lower()

    if email in email_aliases:
        email = email_aliases[email]
    
    if email in email_to_id:
        return email_to_id[email]

    
    i = len(id_to_email) + 1
    id_to_email[i] = email
    email_to_id[email] = i
    unknown_reviewer_emails += [email]
    
    return i

def email_for_id(i):
    return id_to_email(i)


## submitted papers
paper_data = [r for r in read_json(HOTCRP_DATA_JSON) if r['status'] == "submitted"]
print(f"read submission metadata [{HOTCRP_DATA_JSON}]")



## ids 
# these are strings when coming from csv files, 
# so make sure they are strings here
pc_ids = [pc['email'].lower() for pc in pc_data]
paper_ids = [str(p['pid']) for p in paper_data]

print(f"  - {len(pc_ids)} PC members\n  - {len(paper_ids)} submissions\n")

# preference data
pref_data = read_csv(HOTCRP_ALLPREFS_CSV)
print(f"read preference data [{HOTCRP_ALLPREFS_CSV}]")

## READ AND WRITE BIDS FILE

# positive bids, 1..20 with 1 as willing.
bid_data = {
    (p['paper'],p['email'].lower()):int(p['preference']) 
    for p in pref_data 
    if p['preference']
}

def get_bid(pid,rid):
    
    bid = bid_data.get((pid,rid),0)
        
    if bid < 0:
        return 0.05
    
    if bid == 0:
        return 1
    
    # round 1..20 to 3-6
    if bid > 20:
        bid = 20
     
    return round((bid - 1) * (6-3) / (20-1) + 3,2)       
    

bids = [{
    "paper":pid,
    "reviewer":id_for_email(rid),
    "bid": get_bid(pid,rid),
    "reviewer_email":rid
}
    for pid in paper_ids
    for rid in pc_ids
]

write_csv(LCM_BIDS_CSV,bids)
print(f"wrote bids to [{LCM_BIDS_CSV}]")
print()

## WRITE RAW SCORES

# semantic-scholar-scores.csv: reviewerId,reviewerExternalId,submissionId,submissionExternalId,score,reason
try:
    ss_score_data = {
        (ss['submissionExternalId'],ss['reviewerExternalId'].lower())
        :
        round(float(ss['score']),2)
        for ss in read_csv(SS_SCORES_CSV)
    }
    print(f"read semantic scholor scores [{SS_SCORES_CSV}]")
except:
    print(f"could not read semantic scholar scores file [{SS_SCORES_CSV}]")
    ss_score_data = {}
    

# acl-scores.csv: ,paperid,reviewer_email,similarity
try:
    acl_score_data = {
        (acl['paperid'],acl['reviewer_email'].lower())
        :
        round(float(acl['similarity']),2)
        for acl in read_csv(ACL_SCORES_CSV)
    }
    print(f"read ACL scores file [{ACL_SCORES_CSV}]")
except:
    print(f"could not read ACL scores file [{ACL_SCORES_CSV}]")
    acl_score_data = {}

    

# from HOTCRP_ALLPREFS
topic_score_data = {
    (p['paper'],p['email'].lower()):int(p['topic_score']) 
    for p in pref_data
    if p['topic_score']
}


def bounded_or_nothing(lookup,pid,rid):
    if (pid,rid) not in lookup:
        return ""
        
    return bounded(lookup[pid,rid],0,1)

raw_scores = [{
    "paper":pid,
    "reviewer":id_for_email(rid),
    "ntpms":bounded_or_nothing(ss_score_data,pid,rid),
    "nacl":bounded_or_nothing(acl_score_data,pid,rid),
    "nk": bounded((20+topic_score_data.get((pid,rid),0)) / 40,0,1),
    "reviewer_email":rid
}
    for pid in paper_ids
    for rid in pc_ids
]

write_csv(LCM_RAW_SCORES_CSV,raw_scores)
print(f"wrote raw scores [{LCM_RAW_SCORES_CSV}]")

print()

## WRITE CONFLICTS
# reviewerId,reviewerExternalId,submissionId,submissionExternalId,score,reason
try:
    ss_coi_data = {
        (ss['submissionExternalId'],ss['reviewerExternalId'])
        for ss in read_csv(SS_CONFLICTS_CSV) if ss['score']
    }
    print(f"read SS conflict file [{SS_CONFLICTS_CSV}]")
except:
    print(f"could not read SS conflict file [{SS_CONFLICTS_CSV}]")
    ss_coi_data = set()

# paper,author_email,reviewer,conflict
try:
    dblp_coi_data = {
        (d['paper'],d['reviewer'].lower())
        for d in read_csv(DBLP_CONFLICTS_CSV) if d['conflict']
    }
    print(f"read DBLP conflict file [{DBLP_CONFLICTS_CSV}]")
except:
    print(f"could not read DBLP conflict file [{DBLP_CONFLICTS_CSV}]")
    dblp_coi_data = set()



    
hotcrp_coi_data = {
    (p['paper'],p['email']) for p in pref_data if p['conflict'] == "conflict"
}

conflicts = [{
    'paper':pid,
    'reviewer':id_for_email(rid),
    'reviewer_email':rid.lower()
} for (pid,rid) in hotcrp_coi_data | ss_coi_data | dblp_coi_data]


write_csv(LCM_CONFLICTS_CSV,conflicts)
print(f"wrote conflicts [{LCM_CONFLICTS_CSV}]")

print()



# reviewer props: reviewer,role,seniority,conflicted_papers,region,authored

coi_data = read_csv(DATA_WITH_NONREVIEWERS + LCM_CONFLICTS_CSV)

reviewer_cois = {}
for coi in coi_data:
    (pid,rid) = (coi['paper'],coi['reviewer'])
    if rid not in reviewer_cois:
        reviewer_cois[rid] = []
    reviewer_cois[rid] += [int(pid)]
    
print(f"read cois [{LCM_CONFLICTS_CSV}]")

try:
    seniority_data = read_csv(REVIEWER_EXPERIENCE_CSV)
    print(f"read seniority data [{REVIEWER_EXPERIENCE_CSV}]")
except:
    print(f"could not read reviewer experience data [{REVIEWER_EXPERIENCE_CSV}]")
    seniority_data = []

for s in seniority_data:
    s['email'] = s['email'].lower()
    
def get_fullname(record):
    return "{first} {last}".format(**record)
    
name_lookup = {(get_fullname(s)):s for s in seniority_data}
email_lookup = {s['email']:s for s in seniority_data}
    
def get_seniority(pc):
    name = get_fullname(pc)
    
    if pc['email'] in email_lookup:
        record = email_lookup[pc['email']]
    elif name in name_lookup:
        record = name_lookup[name]
    else:
        record = {}
        
    paper_count = int(record.get("paper_count",0))
    pc_count = int(record.get("pc_count",0))

    seniority = 0
    
    if paper_count * pc_count:
        seniority = 1
    
    if min(paper_count,pc_count) >= 3:
        seniority = 2
    
    if paper_count+pc_count >= 15:
        seniority = 3
        
    return seniority
        
    
props = [{
    'reviewer':id_for_email(pc['email']),
    'role':"AC" if "ac" in pc['tags'] else "PC",
    "seniority":get_seniority(pc),
    "conflict_papers":str(reviewer_cois.get(pc['email'],[])),
    "region":''.join(filter(lambda x: str.isalnum(x) and str.isascii(x), pc['affiliation'])),
    "authored":str([]),
    "reviewer_email":pc['email'].lower()
}
    for pc in pc_data
]

write_csv(LCM_REVIEWER_PROPS_CSV,props)
print(f"wrote reviewer props [{LCM_REVIEWER_PROPS_CSV}]")

print()


try:
    coauthor_data = [{
        "reviewer_1":       id_for_email(cd['reviewer_1']),
        "reviewer_2":       id_for_email(cd['reviewer_2']),
        "distance":         cd['distance'],
        "reviewer_1_email": cd['reviewer_1'].lower(),
        "reviewer_2_email": cd['reviewer_2'].lower()
    } for cd in read_csv(COAUTHOR_DISTANCE_FILE_NAME)]
except:
    print(f"could not read SS conflict file [{SS_CONFLICTS_CSV}]")
    coauthor_data = []
    

if coauthor_data:
    write_csv(LCM_COAUTHOR_DISTANCE_CSV, coauthor_data)
    print(f"moved coauthor distance [{COAUTHOR_DISTANCE_FILE_NAME}] to [{LCM_COAUTHOR_DISTANCE_CSV}]")

print()

if unknown_reviewer_emails:
    print(f"found {len(unknown_reviewer_emails)} non-program committee emails:")
    pprint(sorted(unknown_reviewer_emails))

print("done")
