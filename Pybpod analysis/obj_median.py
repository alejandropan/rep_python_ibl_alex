# -*- coding: utf-8 -*-
"""
Created on Thu Jan  3 14:19:48 2019
median values per session for pybpod behavior files
@author: apv2
"""
def obj_median(behav):

    med =[]
    days = list(behav.days.unique())
    for day in days:
        med.append(behav.rt[(behav.days == day)].median())
        
    return med
    
    
    
    
    