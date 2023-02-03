import pandas as pd
# from sklearn.linear_model import LogisticRegression
from sklearn.linear_model import LinearRegression
import logging

logger = logging.getLogger(__name__)

def get_scores_old(config, scores):
    scores['is_positive'] = scores['bid'] >= config['POSITIVE_BID_THR']
    bid2exponent = {'bid':[0.05,1,2,4,6],'exponent': config['HYPER_PARAMS']['bid_inverse_exponents']}
    #[1/0.05, 1.0, 1.0/2, 1.0/4.0 , 1.0/6.0]}
    bid2exponent = pd.DataFrame(bid2exponent)
    scores = scores.reset_index().merge(bid2exponent,how='left',on='bid').set_index(['paper','reviewer'])
    epsilon = 0.0000001

    #match score: avg of ntpms and nacl
    scores['ms'] =  (scores['ntpms']  + scores['nacl'])/2
    #if ntpms is na, then overwrite by nacl
    scores.loc[scores['ntpms'].isna(),'ms'] = scores['nacl'].loc[scores['ntpms'].isna()]
    #if nacl is na, overwrite by ntpms
    scores.loc[scores['nacl'].isna(),'ms'] = scores['ntpms'].loc[scores['nacl'].isna()]

    #agg score: avg of match score and keyword score
    scores['scores_base'] = (scores['ms'] + scores['nk'])/2
    #if match score is na, overwrite by keyword score
    scores.loc[scores['ms'].isna(),'scores_base'] = scores['nk'].loc[scores['ms'].isna()]
    #if keyword score is na, overwrite by match score
    scores.loc[scores['nk'].isna(),'scores_base'] = scores['ms'].loc[scores['nk'].isna()]

    # tweaking based on bid value
    condn = scores['is_positive'] & (scores['nk'] < epsilon)
    #if bid is positive and keyword score < epsilon, overwrite by match score
    scores.loc[condn,'scores_base'] = scores['ms'].loc[condn]

    #if everything is na, score = 0
    scores.loc[scores['scores_base'].isna(),'scores_base'] = 0.0
    #
    scores['score']  = scores['scores_base']**(1.0/scores['exponent'])

    # if score is below this thr, then backoff to keyword score only
    lower_thr = 0.15
    #select all scores less than 0.15
    condn_ll = (scores['score'] <= lower_thr) & (~scores['nk'].isna())
    #recompute them as ((nk)^(1/exponent)).clip(upper=0.15)
    scores.loc[condn_ll,'score'] = (scores['nk'].loc[condn_ll]**(1.0/scores['exponent'].loc[condn_ll])).clip(upper=lower_thr)
    return scores

def get_scores(config, scores):
    # Just a copy of how the old code acquired the scores variable. Hopefully this works.
    scores['is_positive'] = scores['bid'] >= config['POSITIVE_BID_THR']
    bid2exponent = {'bid':[0.05,1,2,4,6],'exponent': config['HYPER_PARAMS']['bid_inverse_exponents']}
    #[1/0.05, 1.0, 1.0/2, 1.0/4.0 , 1.0/6.0]}
    bid2exponent = pd.DataFrame(bid2exponent)
    # I'm VERY skeptical of this step. It looks like it's doing a *dictionary mapping* from raw bids to these ones from the config file.
    # What about all the bids which take on floating point numbers not in that dictionary??
    scores = scores.reset_index().merge(bid2exponent,how='left',on='bid').set_index(['paper','reviewer'])

    # Grab the data that contains labels for use in training our model.
    regressionData = scores[["ntpms", "nacl", "nk", "label"]]
    regressionData = regressionData.loc[regressionData["label"].notna()]
    allThree = regressionData.loc[regressionData["ntpms"].notna() & regressionData["nacl"].notna() & regressionData["nk"].notna()]

    justTPMS = regressionData.loc[regressionData["ntpms"].notna() & regressionData["nk"].notna()]

    justACL = regressionData.loc[regressionData["nacl"].notna() & regressionData["nk"].notna()]

    noTPMSorACL = regressionData.loc[regressionData["nk"].notna()]

    # Run the regressions on our training data.
    allThree_model = LinearRegression()
    allThree_model.fit(allThree.drop("label"), allThree["label"])

    justTPMS_model = LinearRegression()
    justTPMS_model.fit(justTPMS.drop("label"), justTPMS["label"])

    justACL_model = LinearRegression()
    justACL_model.fit(justACL.drop("label"), justACL["label"])

    noTPMSorACL_model = LinearRegression()
    noTPMSorACL_model.fit(noTPMSorACL.drop("label"), noTPMSorACL["label"])

    # Now, grab the data again, but this time *include* rows that don't have labels.
    regressionData = scores[["ntpms", "nacl", "nk"]]
    allThree = regressionData.loc[regressionData["ntpms"].notna() & regressionData["nacl"].notna() & regressionData["nk"].notna()]

    justTPMS = regressionData.loc[regressionData["ntpms"].notna() & regressionData["nk"].notna()]

    justACL = regressionData.loc[regressionData["nacl"].notna() & regressionData["nk"].notna()]

    noTPMSorACL = regressionData.loc[regressionData["nk"].notna()]

    # Initialize the scores_base column with arbitrary copied values from the nk column.
    scores["scores_base"] = 0.0 * scores["nk"]
    # Now override those arbitrary values with the regression scores for each category.
    scores.loc[scores["ntpms"].notna() & scores["nacl"].notna() & scores["nk"].notna(), "scores_base"] = allThree_model.predict(allThree)
    scores.loc[scores["ntpms"].notna() & scores["nacl"].isna() & scores["nk"].notna(), "scores_base"] = justTPMS_model.predict(justTPMS)
    scores.loc[scores["ntpms"].isna() & scores["nacl"].notna() & scores["nk"].notna(), "scores_base"] = justACL_model.predict(justACL)
    scores.loc[scores["ntpms"].isna() & scores["nacl"].isna() & scores["nk"].notna(), "scores_base"] = noTPMSorACL_model.predict(noTPMSorACL)


    # If we obtain a NA score from this process somehow, just set to 0.0. (this seems to be what the old code did)
    scores.loc[scores["scores_base"].isna(), "scores_base"] = 0.0

    # Now, let's clip the results to lie within 0.0 and 1.0. Since we're using a fundamentally different method from the original code, this is necessary.
    scores["score"] = min(1.0, max(0.0, scores["score"]))

    # Now perform the final, wonky exponentiation step.
    scores["score"] = scores["scores_base"]**(1.0 / scores["exponent"])

    print(allThree_model.coef_)
    print(justTPMS_model.coef_)
    print(justACL_model.coef_)
    print(noTPMSorACL_model.coef_)
    return scores

def compute_scores(config=None):

    scores = pd.read_csv(config['RAW_SCORES_FILE'],usecols=["paper","reviewer","ntpms","nacl","nk", "label"]).set_index(['paper','reviewer'])
    bids = pd.read_csv(config['BIDS_FILE'],usecols=["paper","reviewer","bid"]).set_index(['paper','reviewer'])
    scores = scores.join(bids)
    scores['bid'] = scores['bid'].fillna(config['DEFAULT_BID_WHEN_NO_BIDS'])

    scores = get_scores(config,scores)
    scores = scores[['score']]
    num_entries_before = scores.size
    scores = scores.query('score > 0')
    num_entries_after = scores.size
    logger.info(f'Filtered scores <= 0. {(num_entries_before - num_entries_after) / num_entries_before} fraction removed ...')
    logger.info(f"Caching aggregated score to {config['CACHED_SCORES_FILE']} to save time during next run. To recompute, delete this file and rerun this script.")
    scores.to_csv(config['CACHED_SCORES_FILE'])
    return scores
