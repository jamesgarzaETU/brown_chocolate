#!/home/ubuntu/anaconda3/bin/python3 python3
# ***************************************************************************
# Program Title: .../1_process_data_poc.py
# Purpose:       Pull Parquet data from S3 and create HTML file for Sim Dashboard
# Description:   POC version using Parquet-based ETL pipeline instead of SQL
#                SIMS
#                ----
#                86, # Our Code: We respect one another for Partners
#                87, # Our Code: We respect one another for Non-Partners
#
# Programmer:    Martin McSharry / Claude
# Creation Date: 22-December-2024
# Input Files:   S3 Parquet files, code_simulation_3_demographic_data.xlsx
# Output Files:  index.html, data.pkl
# ---------------------------------------------------------------------------
# Revision History
#   22-Dec-2024 - Created POC version using Parquet pipeline
# ***************************************************************************/

import numpy as np
import pandas as pd
import re
from datetime import time, date, datetime, timezone, timedelta
import time
import csv
import sys
import timeit
import math
import random
import os
import shutil
from subprocess import call
import codecs
from shutil import copyfile


# Stats modelling
import statsmodels.formula.api as smf
import statsmodels.api as sm
import scipy

# Logging
import pickle

# Import ETU functions
from skillwell_functions import report, find_ec2, find_rds


# Add skillwell_etl to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from skillwell_etl.pipeline import ParquetPipeline
from skillwell_etl.transform import get_transformed_data_from_parquet
from skillwell_etl import backfill, incremental_update


# Credentials
import json


# ----- Script Timer ----->
start_tm = timeit.default_timer()
script_part_n = 0

# -------------------->
# ----- Sim data ----->
# -------------------->

# Configuration for Parquet-based pipeline
CUSTOMER = 'mckinsey.skillsims.com'
S3_BUCKET = 'etu.appsciences'
server = 'mckinsey.skillsims.com'

sim_id = [
    86, # Our Code: We respect one another for Partners
    87, # Our Code: We respect one another for Non-Partners
]

start_dt = '2025-08-26'
end_dt = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

user_groups = None


# Project dictionary
dict_project = {
    (86, 87): 'Our Code: We Respect One Another'}

script_part_c = 'Start of: ' + server + ', date:' + end_dt

print(script_part_n, ':',  script_part_c)


# <--------------------
# <----- Sim data -----
# <--------------------


# ------------------------------------------->
# ----- Extract sim data from Parquet ------>
# ------------------------------------------->

script_part_n += 1
script_part_c = 'Extracting Data from Parquet (POC)'

print(script_part_n, ':',  script_part_c)

try:


    # Use the new Parquet-based transformation function
    # This replaces: dict_df = extract_data(...)
    with open('mckinsey_our_code_we_respect_data.pkl', 'rb') as f:
        dict_df = pickle.load(f)



except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')

# <-------------------------------------------
# <----- Extract sim data from Parquet ------
# <-------------------------------------------








# ---------------------->
# ----- NPS Scores ----->
# ---------------------->

script_part_n += 1
script_part_c = 'NPS Scores'

print(script_part_n, ':',  script_part_c)

try:
    # Order of Sims
    dict_sim_order = {}
    for i, simid in enumerate(sim_id):
        dict_sim_order.update({simid: i})

    # Check if survey_responses exists
    if 'srv' in dict_df and 'survey_responses' in dict_df['srv'] and dict_df['srv']['survey_responses'] is not None and not dict_df['srv']['survey_responses'].empty:
        # Create a temporary DataFrame for easier chaining
        dict_df['srv']['survey_responses']['optionvalue'] = dict_df['srv']['survey_responses']['optionvalue'].fillna(0)
        temp_df = dict_df['srv']['survey_responses'].copy()

        # The .assign() block now uses np.select for conditional logic
        processed_df = temp_df.assign(
            orderid=0,
            question='NPS Score',

            answer_nps_num=lambda x: x.apply(
                lambda y: int(y['optionvalue']) if pd.notnull(y['answer']) else None, axis=1
            ),

            answer=lambda x: x['answer_nps_num'].apply(
                lambda y: 'Promoter [5-7]' if y in [7, 6, 5] else
                            'Passive [3-4]' if y in [4, 3] else
                            'Detractor [1-2]' if y in [2, 1] else
                            None
            ),

            bar_color=lambda x: np.select(
                [
                    x['answer'].str.contains('Promoter', na=False),
                    x['answer'].str.contains('Passive', na=False)
                ],
                [
                    '#2aa22a',  # Choice for Promoter
                    '#ffffff'   # Choice for Passive
                ],
                default='#c61110'  # Default for Detractor or any other case
            ),

            nps_score=lambda x: np.select(
                [
                    x['answer'].str.contains('Promoter', na=False),
                    x['answer'].str.contains('Passive', na=False),
                    x['answer'].str.contains('Detractor', na=False)
                ],
                [
                    1 * (x['pct'] / 100),    # Promoter score
                    0 * (x['pct'] / 100),    # Passive score
                    -1 * (x['pct'] / 100)    # Detractor score
                ],
                default=None  # Default for any other case
            ),

            n=lambda x: x.groupby(['simid', 'orderid', 'answer'])['n'].transform('sum'),
            pct=lambda x: x.groupby(['simid', 'orderid', 'answer'])['pct'].transform('sum'),

            avg_nps_score=lambda x: x.groupby(['simid', 'orderid'])['nps_score'].transform('sum')
        )

        # Continue with the rest of the chain
        final_df = processed_df.filter([
            'project', 'simid', 'simname', 'orderid', 'question', 'typeid', 'total',
            'answer', 'bar_color', 'n', 'pct', 'avg_nps_score'
        ]).drop_duplicates().assign(
            sim_order=lambda x: x['simid'].map(dict_sim_order) # .map is faster than .apply here
        ).sort_values(
            ['sim_order', 'simid', 'orderid', 'answer']
        )

        # Re-assign the processed data back into the dictionary
        dict_df['srv']['survey_responses'] = pd.concat(
            [dict_df['srv']['survey_responses'], final_df],
            ignore_index=True
        )

        # Update the proj_nps DataFrame
        #dict_df['srv']['survey_responses'].query('orderid == 0')

        temp = pd.concat(
            [dict_df['srv']['survey_responses'].query('orderid == 0'), final_df],
            ignore_index=True
        )
        temp['topic_keywords'] = np.nan

        # Ensure required columns exist before groupby with correct data types
        if 'answerid' not in temp.columns:
            temp['answerid'] = np.nan
        if 'optionvalue' not in temp.columns:
            temp['optionvalue'] = np.nan
        if 'dt' not in temp.columns:
            temp['dt'] = pd.NaT  # Use NaT for datetime64[ns] type
        if 'scale_type' not in temp.columns:
            temp['scale_type'] = None
        if 'topic_analysis' not in temp.columns:
            temp['topic_analysis'] = np.nan  # Use np.nan for float64 type

        temp = temp.groupby(['simid', 'answer','project']).agg({
            'simname': 'first',
            'orderid': 'first',
            'question': 'first',
            'typeid': 'first',
            'total': 'first',
            'bar_color': 'first',
            'n': 'sum',
            'pct': 'sum',
            'avg_nps_score': 'mean',
            'sim_order': 'first',
            'answerid': 'first',
            'optionvalue': 'first',
            'dt': 'first',
            'scale_type': 'first',
            'topic_keywords': 'first',
            'topic_analysis': 'first'
        }).reset_index()
        temp = temp[['project', 'simid', 'simname', 'orderid', 'question', 'typeid', 'total','answer', 'bar_color', 'n', 'pct', 'avg_nps_score',
                     'sim_order', 'answerid', 'optionvalue', 'dt', 'scale_type', 'topic_keywords', 'topic_analysis']]

        # Fix data types to match original SQL output
        temp['total'] = temp['total'].astype('float64')
        temp['sim_order'] = temp['sim_order'].astype('float64')
        # topic_analysis should be float64 (with np.nan for nulls)
        temp['topic_analysis'] = temp['topic_analysis'].astype('float64')

        dict_df['proj']['proj_nps'] = temp
    else:
        print("No survey_responses data available for NPS calculation")


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')

# <----------------------
# <----- NPS Scores -----
# <----------------------




# ------------------------------>
# ----- Change Skill Names ----->
# ------------------------------>

script_part_n += 1
script_part_c = 'Change Skill Names'

print(script_part_n, ':',  script_part_c)

try:
    if 'sim' in dict_df and 'skill_baseline' in dict_df['sim'] and dict_df['sim']['skill_baseline'] is not None and not dict_df['sim']['skill_baseline'].empty:
        dict_df['sim']['skill_baseline'] = dict_df['sim']['skill_baseline']\
        .assign(
            skillname = lambda x: x['skillname'].apply(lambda y: "Overall Performance" if 'overall performance' in str(y).lower() else y)
        )


    if 'sim' in dict_df and 'skill_improvement' in dict_df['sim'] and dict_df['sim']['skill_improvement'] is not None and not dict_df['sim']['skill_improvement'].empty:
        dict_df['sim']['skill_improvement'] = dict_df['sim']['skill_improvement']\
        .assign(
            skillname = lambda x: x['skillname'].apply(lambda y: "Overall Performance" if 'overall performance' in str(y).lower() else y)
        )


    if 'dmg' in dict_df and 'dmg_skill_baseline' in dict_df['dmg'] and dict_df['dmg']['dmg_skill_baseline'] is not None and not dict_df['dmg']['dmg_skill_baseline'].empty:
        dict_df['dmg']['dmg_skill_baseline'] = dict_df['dmg']['dmg_skill_baseline']\
        .assign(
            skillname = lambda x: x['skillname'].apply(lambda y: "Overall Performance" if 'overall performance' in str(y).lower() else y)
        )


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')


# <------------------------------
# <----- Change Skill Names -----
# <------------------------------





# ---------------------------->
# ----- Create HTML file ----->
# ---------------------------->

script_part_n += 1
script_part_c = 'Create HTML file'

print(script_part_n, ':',  script_part_c)

index_html = report(
    dict_df,
    dict_project=dict_project,
    start_date=start_dt,
    end_date=end_dt,
    mckinsey=True,
)

# Create HTML File (POC output)
html_output_path = os.path.join('index_poc.html')
with open(html_output_path, 'w') as outfile:
    outfile.write(index_html)
print(f"Saved POC HTML to {html_output_path}")


# <----------------------------
# <----- Create HTML file -----
# <----------------------------




print('Script Duration: ', str(round((timeit.default_timer() - start_tm)/60, 2)), ' minutes')
print("<----- SCRIPT RUN SUCCESSFUL -----")
os._exit(os.EX_OK)
