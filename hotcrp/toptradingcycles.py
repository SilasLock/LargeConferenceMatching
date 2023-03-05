#!/usr/bin/env python3

from config import *
import util
from pprint import pprint

# only swap reviewers if score less than score threshold
bid_threshold = 5

# no swap if topics are not positive.
topic_score_threshold = 0

#review_types = {("primary","round1")}
review_types = {("meta","final")}


def keyfor(record):
    return (record['paper'],record['email'])

def intzero(value):
    if not value:
        return 0
    else:
        return int(value)

assignment_data = util.read_csv(HOTCRP_PCASSIGNMENT_CSV)
pref_data = util.read_csv(HOTCRP_ALLPREFS_CSV)

original_assignment = {keyfor(r) for r in assignment_data}

# only get positive bids if qualified to swap
#  - positive topic score
#  - no conflict
bid = {
    keyfor(r) : intzero(r['preference'])
    for r in pref_data
    if r['conflict'] != 'conflict'
#    and intzero(r['topic_score']) >= topic_score_threshold
}

def get_bid(paper,reviewer):
    return bid.get((paper,reviewer),0)

topic_score = {keyfor(r):intzero(r['topic_score']) for r  in pref_data}
conflict = {keyfor(r) for r in pref_data if r['conflict'] == 'conflict'}

def favorite(pr,others):
    (p,r) = pr
    
    # do not allow trades if reviewer is already assigned the paper.
    others_less_self = [
        (fp,fr)
        for (fp,fr) in others
        if (fp,r) not in original_assignment
    ] 

    if not others_less_self:
        return (p,r)
    
    return max(others_less_self,key = lambda o: get_bid(o[0],r))


def suffix_from(lst, value):
    return lst[lst.index(value):] if value in lst else []

def any_of(lst):
    return next(iter(lst))

for (t,round) in review_types:

    cycles = []
    
    # current assignment that can be swapped 
    active = {
        keyfor(r)
        for r in assignment_data
        if r['action'] == f"{t}review"
        and bid.get(keyfor(r),0) <= bid_threshold
    }

    # unused
    paper_lookup = {p:(p,r) for (p,r) in active}
    

    
    while active:

        # get edges, self loop if nothing preferred.
        fav = {
            (p,r) : (fp,fr) if get_bid(fp,r) > get_bid(p,r) else (p,r)
            for (p,r) in active
            for (fp,fr) in [favorite((p,r),active)]
        }

        
#        jealous = [(p,f) for (p,f) in fav.items() if p != f]
#        print(f"found {len(jealous)} non-selfloops of {len(active)}")
                
        
        current = any_of(active)
        path = []
        
        while True:
   
            path += [current]
            current = fav[current]

            if current in path:
                break
            
        cycle = suffix_from(path,current)
        #        print(f"found cycle of length {len(cycle)}: {cycle}")

        if len(cycle) > 1:
            cycles += [cycle]
        

        active = active - set(cycle)


    if cycles:
        print("paper,action,email,round,bid,oldbid")
    
    new_assignment = []
    for c in cycles:
        if len(c) > 1:


            for ((tp,tr),(gp,gr)) in zip([c[-1]] + c[:-1],c):

                if (gp,tr) in original_assignment:
                    print(f"DUPLICATE ASSIGNMENT {(gp,tr)}")
                
                print(f"{gp},clearreview,{gr},any,{get_bid(gp,gr)},{get_bid(gp,gr)}")
                print(f"{gp},{t}review,{tr},{round},{get_bid(gp,tr)},{get_bid(tp,tr)}")

                new_assignment += [(gp,tr)]
                
#            print()

    
if len(new_assignment) != len(set(new_assignment)):
    print("ERROR: created duplicate assignment")
       
    
    


