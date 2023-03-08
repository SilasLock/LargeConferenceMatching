import pandas as pd
import numpy as np
import logging
import yaml
from base_ilp import BaseILP, Equation, Objective, Constraints, General
from tqdm import tqdm
from collections import defaultdict

logger = logging.getLogger(__name__)

def to_name(output_files_prefix):
    return output_files_prefix + '.lp'

class MatchingILP(BaseILP):

    def __init__(self,
                paper_reviewer_df,
                reviewer_df,
                distance_df,
                config,
                co_review_vars,
                add_soft_constraints=True,
                fixed_variable_solution_file=None,
                output_files_prefix=''
                ):
        super().__init__()

        self.paper_reviewer_df = paper_reviewer_df
        self.reviewer_df = reviewer_df
        self.distance_df = distance_df
        self.config = config
        self.add_soft_constraints = add_soft_constraints
        self.co_review_vars = co_review_vars
        self.bidding_cycles = None
        self.fixed_variable_solution_file = fixed_variable_solution_file
        if fixed_variable_solution_file:
            df = pd.read_csv(self.fixed_variable_solution_file).drop_duplicates()
            self.fixed_solution_pairs = list(zip(df.paper,df.reviewer))
            self.membership = {
                role:set(reviewer_df.query(f'role == "{role}"').index)
                for role in ["PC","SPC","AC"]
            }
            self.all_committee = set(reviewer_df.index)
        self.output_files_prefix= output_files_prefix
        self.rejected_papers = set()
        if "REJECTED_PAPERS_FILE" in config:
            if config["REJECTED_PAPERS_FILE"]:
                # Produce a Python set that contains all paper IDs that have been rejected.
                self.rejected_papers = pd.read_csv(config["REJECTED_PAPERS_FILE"])["paper"].agg(set)
                logger.info(f"Found {len(self.rejected_papers)} rejected papers to which we won't add new reviewers.")

    def create_ilp(self,lp_filename=''):

        #TODO: Check that every paper has reviewers and vice versa

        logger.info('Reviewer matching objective')
        self.add_reviewer_matching_objective()

        logger.info('Paper capacity')
        self.add_paper_capacity_constraints()

        logger.info('Reviewer capacity')
        self.add_reviewer_capacity_constraints()

        # This last one is the EC-specific constraint we added--that we need at least one computer scientist per paper.
        logger.info('CS expertise')
        self.add_computer_science_constraints()

        if self.fixed_variable_solution_file is not None:
            logger.info('Setting fixed assignements')
            self.set_fixed_vars()


        if self.add_soft_constraints:
            logger.info('Coreview Constraints')
            self.add_coreview_constraints()
            logger.info('Co-author distance Objective')
            self.add_coreview_distance_objective()

            logger.info('Seniority Objectives')
            self.add_seniority_reward()

            logger.info('Region Objective')
            self.add_region_objective()

            logger.info('Region Constraints and bounds')
            self.add_region_constraints_and_bounds()

            logger.info('Cycle Bounds')
            self.populate_bidding_cycles()
            self.add_cycle_constraints()
            self.add_cycle_objective()

            for (role,pen_dict) in self.config['HYPER_PARAMS']['paper_distribution_pen'].items():
                if pen_dict:
                    self.add_paper_distribution_constraints_obj_limits(role,pen_dict)

        logger.info('Start writing! Phew!')

        self.write_to_file(lp_filename)
        logger.info("Wrote out %s to file" % lp_filename)
        # Write out yml file for managing experiments
        yml_filename = lp_filename.replace('lp','yml')
        with open(yml_filename, 'w') as fh:
            yaml.dump(self.config, fh)
        logger.info('End writing! Phew!')

    '''*********** Objective function **********'''
    def add_reviewer_matching_objective(self):
        paper_reviewer_tuples = self.paper_reviewer_df.index.values
        matching_vars = ['x{}_{}'.format(i,j) for i, j in paper_reviewer_tuples]
        self.binary.add(matching_vars)
        matching_vars_scores = [self.paper_reviewer_df.loc[(i, j)]['score'].item() for i,j in paper_reviewer_tuples]
        eqn = Equation('obj','',list(zip(matching_vars, matching_vars_scores)), None, None)
        self.objective.add(eqn)

    '''*********** Capacity Constraints **********'''
    # Restrict number of papers that can be assigned to a given reviewer
    def add_reviewer_capacity_constraints(self):
        all_eqns = []

        for rid, role in tqdm(self.reviewer_df['role'].items(), total=self.reviewer_df.index.size, desc="Building reviewer capacity constraints..."):

            papers = list(self.paper_reviewer_df.query(f'reviewer == {rid}').index.get_level_values('paper'))

            rhs_max = self.config['HYPER_PARAMS'][f'max_papers_per_reviewer_{role}']

            ## add missing papers from fixed solution, if any
            if self.fixed_solution_pairs:
                tracked_pairs = {(int(p),int(rid)) for p in papers}
                fixed_pairs = {(int(p),int(r)) for (p,r) in self.fixed_solution_pairs if int(r) == int(rid)}
                diff_pairs = fixed_pairs - tracked_pairs
                missing_papers = [p for (p,r) in diff_pairs]

                # fixed assignment is more than allowed in constraints; increase constraints.
                if rhs_max < len(fixed_pairs):
                    logger.info(f"reviewer {rid} matched to {len(fixed_pairs)} > {rhs_max} papers, increasing capacity")
                    rhs_max = len(fixed_pairs)

                if missing_papers:
                    logger.info(f"for reviewer {rid} adding missing papers {missing_papers}")

                papers += missing_papers

            paper_vars = list(map(lambda x: 'x{}_{}'.format(x,rid),papers))
            coefs = [1]*len(paper_vars)

            oper_max = '<='
            eqn_max = Equation(eqn_type='cons',name='reviewer_capacity_{}_{}'.format(rid, role),
                  var_coefs=list(zip(paper_vars,coefs)),oper=oper_max,
                  rhs=rhs_max)

            all_eqns.append(eqn_max)


            rhs_min = self.config['HYPER_PARAMS'].get(f'min_papers_per_reviewer_{role}',0)
            if rhs_min:
                oper_min = '>='
                eqn_min = Equation(eqn_type='cons',name='reviewer_minimum_{}_{}'.format(rid, role),
                    var_coefs=list(zip(paper_vars,coefs)),oper=oper_min,
                    rhs=rhs_min)

                all_eqns.append(eqn_min)

        self.constraints.add(all_eqns)

    # Restrict number of reviewers that can be assigned to a given paper
    def add_paper_capacity_constraints(self): #1
        all_eqns = []

        rejection_record = []
        for group_name, group in self.paper_reviewer_df.reset_index().groupby(['paper','role']):
            reviewers = list(group['reviewer'])
            pid = group_name[0]
            role = group_name[1]


            # If this paper is rejected, make sure no one new is assigned to it. Otherwise, cap the reviewers at max_reviewers_per_paper_{role}.
            rhs = self.config['HYPER_PARAMS'][f'max_reviews_per_paper_{role}'] if pid not in self.rejected_papers else 0

            ## add missing reviewers from fixed solution
            if self.fixed_solution_pairs:
                tracked_pairs = {(int(pid),int(r)) for r in reviewers}
                fixed_pairs = {
                    (int(p),int(r))
                    for (p,r) in self.fixed_solution_pairs
                    if int(p) == int(pid)
                    and (int(r) in self.membership[role]                  # make sure it's the right role
                    or role == "PC" and int(r) not in self.all_committee) # external reviewers treated as PC
                }
                diff_pairs = fixed_pairs - tracked_pairs
                missing_reviewers = [r for (p,r) in diff_pairs]

                ## if fixed-solution has more matches than RHS, increase RHS.
                if rhs < len(fixed_pairs):
                    # fixed assignment is more than allowed in constraints; increase constraints.
                    if rhs != 0: # do not print for rejected papers
                        logger.info(f"paper {pid} matched to {len(fixed_pairs)} > {rhs} reviewers, increasing capacity")
                    rhs = len(fixed_pairs)

                if missing_reviewers:
                    logger.info(f"for papers {pid} adding missing reviewers {missing_reviewers}")

                reviewers += missing_reviewers
                ### THIS IS UNNEEDED NOW SINCE WE INCREASE RHS TO FIXED AMOUNT
                # if pid in self.rejected_papers:
                #     # If this paper is rejected, we only want to put a constraint on the reviewers who aren't already assigned to it.
                #     pairs_not_in_fixed_matching = tracked_pairs - fixed_pairs
                #     reviewers = [r for (p,r) in pairs_not_in_fixed_matching]
                #     logger.info(f"Paper {pid} was rejected, so we won't add new reviewers for it.")
                #     rejection_record.append(pid)

            reviewer_vars = list(map(lambda x: 'x{}_{}'.format(pid,x),reviewers))
            coefs = [1]*len(reviewer_vars)
            oper = '<=' if self.config['HYPER_PARAMS']['relax_paper_capacity'] else '='

            eqn_ac = Equation(eqn_type='cons',name='paper_capacity_{}_{}'.format(role,pid),
                  var_coefs=list(zip(reviewer_vars,coefs)),oper=oper,
                  rhs=rhs)
            all_eqns.append(eqn_ac)

        logger.info(f"We counted {len(rejection_record)} (paper, role) pairs with a rejected paper, so we should have found 3 times as many such pairs as rejected papers.")
        self.constraints.add(all_eqns)

    # Require a certain number of computer scientists per paper (now a soft constraint)
    def add_computer_science_constraints(self):
        all_eqns = []

        for group_name, group in self.paper_reviewer_df.reset_index().groupby('paper'):
            reviewers = group['reviewer']
            # We're assuming that the new reviewer data has a column called "computer_scientist", which has a Boolean for whether they qualify as one.
            computer_science_expertise = group['computer_scientist']
            pid = group_name

            cs_p = f'cs_{pid}'

            cs_vars = list(map(lambda x: 'x{}_{}'.format(pid, x), reviewers))
            cs_vars.append(cs_p)
            coefs = list(map(lambda x: x, computer_science_expertise))
            coefs.append(-1)
            # cs_p can't be more than the computer scientists assigned to the paper.
            eqn_ac = Equation(eqn_type='cons',name='cs_sum_over_cs_{}'.format(pid),
                  var_coefs=list(zip(cs_vars, coefs)), oper=">=",
                  rhs=0)
            # cs_p can't be more than 1.
            eqn_ac = Equation(eqn_type='cons',name='cs_expertise_{}'.format(pid),
                  var_coefs=[(cs_p, 1)], oper="<=",
                  rhs=1)
            all_eqns.append(eqn_ac)
            self.objective.add(Equation('obj', '', [(cs_p, 10)], None, None))

        self.constraints.add(all_eqns)

    '''*********** Soft constraints **********'''
    # Set coreview vars. coreview_ij at least 0. If x_ij and x_ji, then coreview_ij must be at least 1.
    def add_coreview_constraints(self):
        #[Constraint] coreviews_jj’ >= x_ij + x_ij’ - 1
        #(for all j, j’, i, j and j’ in PC)

        if self.co_review_vars is None:
            logger.warning("Co review var empty. Not adding any coreview constraints")
            return

        pairs = list(map(lambda x: 'coreview{}_{}'.format(x[0],x[1]), self.co_review_vars))
        self.bounds.add(pairs,[0]*len(pairs),None)
        self.general.add(pairs)

        for (rid_i, rid_j, this_pid) in self.co_review_vars:
            co_review_var = 'coreview{}_{}'.format(rid_i,rid_j)
            eqn_vars = [co_review_var, 'x{}_{}'.format(this_pid,rid_i), 'x{}_{}'.format(this_pid,rid_j)]
            coefs = [1.0, -1.0, -1.0]
            eqn = Equation(eqn_type='cons',name='coreview_{}_{}_{}'.format(this_pid, rid_i, rid_j),
                        var_coefs=list(zip(eqn_vars,coefs)),oper='>=',rhs=-1)
            self.constraints.add(eqn)

    def add_coreview_distance_objective(self): #6
        # Only want to penalize when no AC involved

        if self.co_review_vars is None:
            logger.warning("Co review var empty. Cannot contruct coauthor distance constraints")
            return

        def add(distance_df, penalty):
            # Take to take set over the i,j sets. Here we are taking set over
            reviewer_pairs_within_distance = set(distance_df.index.values)
            coreviewer_var_pairs = set((i,j) for (i, j, _) in self.co_review_vars)
            pairs_to_add = coreviewer_var_pairs.intersection(reviewer_pairs_within_distance)
            dis_vars = [f'coreview{i}_{j}' for (i, j) in pairs_to_add]
            logger.info(f'Adding {len(dis_vars)} distance penalties of {penalty}')
            pen = [penalty] * len(dis_vars)
            eqn = Equation('obj','',list(zip(dis_vars, pen)), None, None)
            self.objective.add(eqn)

        # Filter out ACs from distance dataframe
        ac_reviewers = self.reviewer_df.query(f'role == "AC"').index.values
        distance_df = self.distance_df.query('reviewer_1 not in @ac_reviewers').query('reviewer_2 not in @ac_reviewers')

        add(distance_df.query(f'distance == 0'), self.config['HYPER_PARAMS']['coreview_dis0_pen'])
        add(distance_df.query(f'distance == 1'), self.config['HYPER_PARAMS']['coreview_dis1_pen'])


    def add_seniority_reward(self):

        for paper in tqdm(self.paper_reviewer_df.index.unique('paper'), desc="Building seniority constraints..."):

            pc_rids = self.paper_reviewer_df.query(f'paper == {paper} and role=="PC"').index.get_level_values('reviewer')
            pc_vars = list(map(lambda x: 'x{}_{}'.format(paper,x),pc_rids))

            if len(pc_vars) == 0:
                raise Exception(f'Paper {paper} has no PC reviewers!')

            seniorities = list(-1 * self.reviewer_df.loc[pc_rids]['seniority'].values)
            coefs = seniorities

            sen_slack_var = 'sen_slack_{}'.format(paper)
            self.bounds.add(sen_slack_var, low=self.config['HYPER_PARAMS']['min_seniority'], up=self.config['HYPER_PARAMS']['target_seniority'])
            self.general.add(sen_slack_var)
            pc_vars.append(sen_slack_var)
            coefs.append(1)
            eqn_slbalance = Equation(eqn_type='cons',
                              name='sen_slack_{}'.format(paper),
                              var_coefs=list(zip(pc_vars,coefs)),oper='<=',
                              rhs= 0
                             )
            self.constraints.add(eqn_slbalance)

            # Reward objective function by slack var
            var_coefs = [(sen_slack_var, self.config['HYPER_PARAMS']['sen_reward'])]
            eqn = Equation('obj', 'sen_reward_{}'.format(paper), var_coefs, None, None)
            self.objective.add(eqn)

    def add_region_objective(self): #5
        #(5) Region. Reward for every additional region on a paper
        #optimize  Reward*(reg_i)

        region_count_vars = ['region{}'.format(pid) for pid in self.paper_reviewer_df.index.unique('paper')]
        region_reward = self.config['HYPER_PARAMS']['region_reward']
        var_coefs = list(zip(region_count_vars,[region_reward]*len(region_count_vars)))
        eqn = Equation('obj','region',var_coefs,None,None)
        self.objective.add(eqn)

    def add_region_constraints_and_bounds(self): #5
        #1st constraint
        #[Constraint] reg_i <= Sum_{Regions R} reg_iR
        #[Constraint] reg_iR <= Sum_{j are PC+SPC members s.t. Region_j=R}x_ij
        eqns = []
        regions = self.reviewer_df['region'].unique()
        for pid in self.paper_reviewer_df.index.unique('paper'):
            this_vars = ['region{}'.format(pid)] + ['region{}_{}'.format(pid,this_region) for this_region in regions]
            this_coefs = [1] + [-1]*len(regions)
            eqn = Equation('cons','region_{}'.format(pid),list(zip(this_vars,this_coefs)),'<=',0)
            eqns.append(eqn)

        self.constraints.add(eqns)

        eqns = []
        all_region_vars = []
        for region, region_df in self.reviewer_df.query("role != 'AC'").groupby('region'):
            region_rids = region_df.index
            for pid, pid_df in self.paper_reviewer_df.groupby(level='paper'):
                region_reviewers = set(region_rids).intersection(set(pid_df.index.get_level_values('reviewer')))
                region_vars = ['region{}_{}'.format(pid,region)]
                this_vars = region_vars + [ 'x{}_{}'.format(pid,x) for x in region_reviewers]
                all_region_vars += region_vars
                this_coefs = [1] + [-1]*len(region_reviewers)
                eqn = Equation('cons','region_{}_{}'.format(pid,region),list(zip(this_vars,this_coefs)),'<=',0)
                eqns.append(eqn)

        self.constraints.add(eqns)

        #add the bounds
        #reg_iR <= 1 [Bounds]
        self.bounds.add(all_region_vars,None,[1]*len(all_region_vars))

    def populate_bidding_cycles(self):
        # Create a dict mapping from paper to list of authors
        paper_to_authors = defaultdict(list)
        for reviewer, row in self.reviewer_df.iterrows():
            for paper in row['authored']:
                paper_to_authors[paper].append(reviewer)

        self.bidding_cycles = []
        # Only interested in high bids
        filtered_paper_reviewer_df = self.paper_reviewer_df.query(f"bid >= {self.config['POSITIVE_BID_THR']}  and role != 'AC'")
        # Bidding cycles only occur for reviewers who are also authors - not reviewers with no submissions
        filtered_reviewer_df = self.reviewer_df.query("role != 'AC' and authored_any")

        for reviewer_1, group in tqdm(filtered_paper_reviewer_df.groupby(level=1), total=filtered_paper_reviewer_df.reset_index()['reviewer'].nunique(), desc='Building bidding cycles...'):
            reviewer_1_high_bid_papers = group.reset_index()['paper'].values
            reviewer_1_authored_papers = self.reviewer_df.loc[reviewer_1]['authored']
            for paper_1 in reviewer_1_high_bid_papers:
                for reviewer_2 in paper_to_authors[paper_1]:
                    if reviewer_1 < reviewer_2:
                        # Reviewer 1 bid high on paper_1, which revivewer_2 authored. Find any "paper_2" such that paper_2 is written by reviewer_1 and reviewer_2 bid highly on it
                        for paper_2 in filtered_paper_reviewer_df.query(f"reviewer == {reviewer_2} and paper in @reviewer_1_authored_papers").index.get_level_values('paper'):
                            self.bidding_cycles.append((reviewer_1, reviewer_2, paper_1, paper_2))

        self.bidding_cycles = list(set(self.bidding_cycles))

    def add_cycle_constraints(self): #7
        # self.bidding_cycles
        #cycle_jj’ >= x_ij + x_i’j’ - 1
        #(for all i, j, j’ such that i is  written by j’ and i’ is written by j, B_ij’>0, B_i’j>0, j and j’ in SPC+PC)

        #list of (r1,r2,p1,p2): r1 bids on p1 authored by r2 bids on p2 authored by r1
        #i.e.  list of (j, j', i, i')
        if not self.bidding_cycles:
            logger.info("No bidding cycles to add...")
            return


        bidding_cycle_vars = ["cycle{}_{}".format(x[0],x[1]) for x in self.bidding_cycles]
        self.bounds.add(bidding_cycle_vars,[0]*len(bidding_cycle_vars),None)
        self.general.add(bidding_cycle_vars)

        coefs = [1, -1, -1]
        eqns = []
        for this_cycle in self.bidding_cycles:
            j,jp,i,ip = this_cycle
            cycle_vars = ['cycle{}_{}'.format(j,jp), 'x{}_{}'.format(i,j), 'x{}_{}'.format(ip,jp)]
            eqn = Equation('cons','cycle_ip{}_jp{}_i{}_j{}'.format(ip,jp,i,j),list(zip(cycle_vars,coefs)),">=",-1)
            eqns.append(eqn)
        self.constraints.add(eqns)


    def add_cycle_objective(self): #7
        #optimize Penalty*(cycle_
        for this_cycle in self.bidding_cycles:
            j,jp,i,ip = this_cycle

        coefs = [self.config['HYPER_PARAMS']['cycle_pen']]*len(self.bidding_cycles)
        bidding_cycle_vars = ["cycle{}_{}".format(x[0],x[1]) for x in self.bidding_cycles]
        eqn = Equation('obj','',list(zip(bidding_cycle_vars,coefs)),None,None)
        self.objective.add(eqn)

    def add_paper_distribution_constraints_obj_limits(self,role,pen_dict):

        # get keys from pen_dict itself.
        num_papers_list = sorted(pen_dict.keys())

        vars_for_objective = []
        obj_coefs = []
        #iterate over each reviewer
        for reviewer in self.reviewer_df.query(f'role == "{role}"').index:
            #get valid papers for j
            papers = self.paper_reviewer_df.query(f'reviewer == {reviewer}').index.get_level_values('paper')
            for num_papers in num_papers_list:
                slack_var = 'paper_dist{}_{}'.format(reviewer,num_papers)
                dist_vars = ['x{}_{}'.format(paper,reviewer) for paper in papers] + [slack_var]
                coefs = [1]*(len(dist_vars) -1 ) + [-1]
                #add constraint
                eqn = Equation('cons','paper_dist{}_{}'.format(reviewer,num_papers), list(zip(dist_vars,coefs)),'<=', num_papers)
                self.constraints.add(eqn)

                #add bound
                self.bounds.add(slack_var,low=0,up=None)
                #add to objective vars
                vars_for_objective.append(slack_var)
                obj_coefs.append(pen_dict[num_papers])
                #
        obj_eqn = Equation('obj','paper_dist_obj',list(zip(vars_for_objective,obj_coefs)),None,None)
        self.objective.add(obj_eqn)

    def set_fixed_vars(self):
        logger.info("Fixing previous variable assignments from %s..." % self.fixed_variable_solution_file)
        pairs = self.fixed_solution_pairs
        eqns = []
        dropped = []
        for (pid,rid) in pairs:
            match_var = 'x{}_{}'.format(pid,rid)
            coef = 1
            eqn = Equation('cons','fix_assigned_x{}_{}'.format(pid,rid),[(match_var, coef)],"=",1)
            eqns.append(eqn)
        self.constraints.add(eqns)
