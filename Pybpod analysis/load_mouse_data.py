﻿"""
Created by @????  IBL
Edited : 2018-01-03 @alejandro Princeton IBL
   - Current version solves some issues with 2018 pbypod files.
   - Works with matlab files from 2018 as well.
   - Current version is probably suboptimal. It's more of a quick fix.

"""

from oneibl.one import ONE
import pandas as pd
import numpy as np
from os import listdir, getcwd
from os.path import isfile, join
import re
from IPython import embed as shell

one = ONE() # initialize
# one = ONE(base_url='https://dev.alyx.internationalbrainlab.org')

# ==================== #
# ONE/ALYX
# ==================== #

def get_weights(mousename):

    wei = one.alyx.get('/weighings?nickname=%s' %mousename)
    wei = pd.DataFrame(wei)
    wei['date_time'] = pd.to_datetime(wei.date_time)
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')  
    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    return wei

def get_water(mousename):
    wei = one.alyx.get('/water-administrations?nickname=%s' %mousename)
    wei = pd.DataFrame(wei)
    wei['date_time'] = pd.to_datetime(wei.date_time)

    # for w in wei:
    # wei['date_time'] = isostr2date(wei['date_time'])
    wei.sort_values('date_time', inplace=True)
    wei.reset_index(drop=True, inplace=True)
    wei['date'] = wei['date_time'].dt.floor('D')  

    wei['days'] = wei.date - wei.date[0]
    wei['days'] = wei.days.dt.days # convert to number of days from start of the experiment

    return wei

def get_water_weight(mousename):

    wei = get_weights(mousename)
    wa = get_water(mousename)
    wa.reset_index(inplace=True)

    # also grab the info about water restriction
    restr = one.alyx.get('/subjects/%s' %mousename)
    
    # make sure that NaNs are entered for days with only water or weight but not both
    combined = pd.merge(wei, wa, on="date", how='outer')
    combined = combined[['date', 'weight', 'water_administered', 'water_type']]

    # only if the mouse is on water restriction, add its baseline weight
    if restr['last_water_restriction']:
        
        # remove those weights below current water restriction start
        if restr['responsible_user'] == 'valeria':
            combined = combined[combined.date >= pd.to_datetime(restr['last_water_restriction'])]

        baseline = pd.DataFrame.from_dict({'date': pd.to_datetime(restr['last_water_restriction']), 
            'weight': restr['reference_weight'], 'index':[0]})

        # add the baseline to the combined df
        combined = combined.append(baseline, sort=False)

    else:
        baseline = pd.DataFrame.from_dict({'date': None, 'weight': combined.weight[0], 'index':[0]})

    combined = combined.sort_values(by='date')
    combined['date'] = combined['date'].dt.floor("D") # round the time of the baseline weight down to the day

    combined = combined.reset_index()
    combined = combined.drop(columns='index')

    # also indicate all the dates as days from the start of water restriction (for easier plotting)
    combined['days'] = combined.date - combined.date[0]
    combined['days'] = combined.days.dt.days # convert to number of days from start of the experiment

    return combined, baseline

def get_behavior(mousename, **kwargs):

    # find metadata we need
    eid, details = one.search(subjects=mousename, details=True, **kwargs)

    # sort by date so that the sessions are shown in order
    start_times  = [d['start_time'] for d in details]
    eid          = [x for _,x in sorted(zip(start_times, eid))]
    details      = [x for _,x in sorted(zip(start_times, details))]

    # grab only behavioral datatypes, all start with _ibl_trials
    types       = one.list(eid)
    types2      = [item for sublist in types for item in sublist]
    types2      = list(set(types2)) # take unique by converting to a set and back to list
    dataset_types = [s for i, s in enumerate(types2) if '_ibl_trials' in s]
    
    # load data over sessions
    for ix, eidx in enumerate(eid):
        dat = one.load(eidx, dataset_types=dataset_types, dclass_output=True)

        # skip if no data, or if there are fewer than 10 trials in this session
        if len(dat.data) == 0:
            continue
        else:
            try:
                if len(dat.data[0]) < 10:
                    continue
            except:
                continue
    
        # pull out a dict with variables and their values
        tmpdct = {}
        for vi, var in enumerate(dat.dataset_type):
            #k = [item[0] for item in dat.data[vi]] #2018-01-03 @alejandro It doesn't work with pybpod from Dec2018 version. 
            #For now I'm going to turn nan = 0. 
           k=[]
           for item in dat.data[vi]:
               item = np.nan_to_num(item)
               if len(np.atleast_1d(item))>1:
                   k.append(item[0])
               else:
                   ## 2018-01-04 @alejandro - These try/except statements permits the use of matlab and pybpod. 
                   #Some pybpod data comes as numpy.float64 which is not iterable - item[0] will fail
                   #Without item[0], matlab files will fail at line 186 while creating choice 2. 
                   #For some weird reason pandas replace will read objects [-1] or [1] but not [0]
                   try:
                       k.append(item[0])
                   except: 
                       k.append(item)
            
            # 2018-01-03 @alejandro -  CAUTION: This applies a stim time of 0 to weird trials where the stim doesnt  come on. 
            #These trials need to be removed afterwards outside the function
           for x in range(len(k)):
                if np.array(k[x]).size == 0:
                    k[x] = 0
                    
           tmpdct[re.sub('_ibl_trials.', '', var)] = k

        # add crucial metadata
        tmpdct['subject']       = details[ix]['subject']
        tmpdct['users']         = details[ix]['users'][0]
        tmpdct['lab']           = details[ix]['lab']
        tmpdct['session']       = details[ix]['number']
        tmpdct['start_time']    = details[ix]['start_time']
        tmpdct['end_time']      = details[ix]['end_time']
        tmpdct['trial']         = [i for i in range(len(dat.data[0]))]

        # append all sessions into one dataFrame
        if not 'df' in locals():
            df = pd.DataFrame.from_dict(tmpdct)
        else:
            df = df.append(pd.DataFrame.from_dict(tmpdct), sort=False, ignore_index=True)
            
    ##2018-01-03 @alejandro Remove error trials
        #df = df.drop(to_del)
    # take care of dates properly
    df['start_time'] = pd.to_datetime(df.start_time)
    df['end_time']   = pd.to_datetime(df.end_time)
    df['date']       = df['start_time'].dt.floor("D")

    # convert to number of days from start of the experiment
    df['days']       = df.date - df.date[0]
    df['days']       = df.days.dt.days 

    # add some more handy things
    df['rt']        = df['response_times'] - df['stimOn_times']

    df['signedContrast'] = (- df['contrastLeft'] + df['contrastRight']) * 100
    df['signedContrast'] = df.signedContrast.astype(int)

    # flip around choice coding - go from wheel movement to percept
    df['choice'] = -1*df['choice']
    df['correct']   = np.where(np.sign(df['signedContrast']) == df['choice'], 1, 0)
    df.loc[df['signedContrast'] == 0, 'correct'] = np.NaN
    df['choice2'] = df.choice.replace([-1, 0, 1], [0,np.nan, 1]) # code as 0, 100 for percentages
    #df['probabilityLeft'] = df.probabilityLeft.round(decimals=2)# 2018-01-03 @alejandro -  Probability left not present in pybpod
    df = df.drop(list(df.index[df.stimOn_times == 0])) #@alejandro to remove error trial where there is no value for StimOnset
    return df
 