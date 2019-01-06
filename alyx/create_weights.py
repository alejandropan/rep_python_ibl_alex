# -*- coding: utf-8 -*-
"""
Created on Wed Jan  2 13:06:43 2019

@author: apv2
Update eights in Alyx from csv with dates subjects and weights 
2019-01-02
"""

from oneibl.one import ONE
import pandas as pd

one = ONE(base_url='https://alyx.internationalbrainlab.org')

weightings = pd.read_csv('C://Users/apv2/Documents/IBL/Dec2018_weightings.csv' )


# sub = one.alyx.rest('subjects', 'list', '?alive=True&project=ibl_zadorlab&water_restricted=True')

dates = list(weightings.Date)


sub = ['ibl_witten_01',
       'ibl_witten_02',
       'ibl_witten_03']



for dat in dates:
    for s in sub:

        we_ = {
            'subject': s,
            'date_time': dat,
            'weight':  float(weightings [s] [weightings.Date == dat]),
            'user': 'alejandro',
            }

        rep = one.alyx.rest('weighings', 'create', we_)