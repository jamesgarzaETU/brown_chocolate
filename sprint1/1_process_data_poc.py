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


import pymysql
import numpy as np
import pandas as pd
import paramiko
import re
from datetime import time, date, datetime, timezone, timedelta
import time
import csv
import sys
import timeit
from sshtunnel import SSHTunnelForwarder
import math
import random
import os
import shutil
from subprocess import call
from jinja2 import Environment, FileSystemLoader
import codecs
from shutil import copyfile
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build 

# Stats modelling
import statsmodels.formula.api as smf
import statsmodels.api as sm
import scipy

# Google Sheets
import pygsheets

# Logging
import logging
import pickle

# Import ETU functions
sys.path.append('/home/ubuntu/etu_appliedsciences/_code_libraries/python')
from skillwell_functions import report, find_ec2, find_rds


# Add skillwell_etl to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from skillwell_etl.pipeline import ParquetPipeline
from skillwell_etl.transform import get_transformed_data_from_parquet
from skillwell_etl import backfill, incremental_update

# Change working directory to python script location
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Credentials
import json
credentials = json.load(open("{}/credentials.json".format('/home/ubuntu/etu_appliedsciences/_credentials'), "r"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- Log file ----->
log = logging.getLogger(os.path.basename(__file__))
hdlr = logging.FileHandler(os.path.basename(__file__) + '.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
log.setLevel(logging.INFO)

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
log.info(str(script_part_n) + ':' +  script_part_c)


# <--------------------
# <----- Sim data -----
# <--------------------


# ----------------------------------------->
# ----- Check/Update Parquet Data --------->
# ----------------------------------------->

script_part_n += 1
script_part_c = 'Check/Update Parquet Data'

print(script_part_n, ':', script_part_c)
log.info(str(script_part_n) + ':' + script_part_c)

try:
    logger.info("Checking data freshness...")
    
    # Run backfill to ensure all tables exist (skips existing)
    try:
        logger.info("Running Backfill check...")
        backfill.main()
    except Exception as e:
         logger.error(f"Backfill failed: {e}")

    # Run incremental update to get latest data
    try:
        logger.info("Running Incremental Update check...")
        incremental_update.main()
    except Exception as e:
         logger.error(f"Incremental update failed: {e}")
         
    # Initialize pipeline for analysis
    pipeline = ParquetPipeline(s3_bucket=S3_BUCKET, customer=CUSTOMER)

except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':', script_part_c, ':', str(e))
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
    # Don't exit - try to continue with existing data
    logger.warning("Continuing with existing Parquet data...")

# <-----------------------------------------
# <----- Check/Update Parquet Data ---------
# <-----------------------------------------


# ---------------------------->
# ----- Demographic Data ----->
# ---------------------------->

script_part_n += 1
script_part_c = 'Demographic Data'

print(script_part_n, ':',  script_part_c)
log.info(str(script_part_n) + ':' +  script_part_c)

try:
    # Pipeline already initialized in Check/Update section
    # Load raw data from Parquet to get language/user info for demographics
    # NOTE: Do NOT pass date filters here - let filter_logs_and_users handle date filtering
    # to match original SQL behavior (which calculates first_start_dt before filtering)
    print("Loading raw data from Parquet files...")
    raw_data = pipeline.load_raw_data_for_analysis(
        sim_ids=sim_id
    )
    print(f"Loaded {len(raw_data)} tables from Parquet")

    # Get language from user_sim_log (first completed attempt) - replaces SQL query
    df_logs = raw_data.get('user_sim_log')
    df_user = raw_data.get('user')
    df_language = raw_data.get('language')

    if df_logs is not None and df_user is not None and df_language is not None:
        # Filter completed logs
        if df_logs['complete'].dtype == object:
            complete_mask = df_logs['complete'].apply(lambda x: int.from_bytes(x, "big") if isinstance(x, bytes) else int(x) if pd.notnull(x) else 0) == 1
        else:
            complete_mask = df_logs['complete'] == 1

        df_completed = df_logs[complete_mask].copy()
        df_completed = df_completed.sort_values(['simid', 'userid', 'end'])
        df_completed['attempt'] = df_completed.groupby(['simid', 'userid']).cumcount() + 1
        # Handle column name variations (languageId vs languageid)
        lang_col = 'languageId' if 'languageId' in df_completed.columns else 'languageid'
        df_first_attempt = df_completed[df_completed['attempt'] == 1][['userid', lang_col]].drop_duplicates()
        df_first_attempt = df_first_attempt.rename(columns={lang_col: 'languageid'})

        # Join with user and language tables (role=1 filter)
        df_user_filtered = df_user[df_user['roleid'] == 1] if 'roleid' in df_user.columns else df_user

        df_demog = df_first_attempt.merge(
            df_user_filtered[['userid', 'uid']],
            on='userid',
            how='left'
        ).merge(
            df_language[['id', 'name']].rename(columns={'id': 'languageid', 'name': 'Language'}),
            on='languageid',
            how='left'
        )

        # Add Language_ord column
        df_demog['Language_ord'] = df_demog['languageid']

        logger.info(f"Demographics from Parquet: {len(df_demog)} users")
    else:
        df_demog = pd.DataFrame()
        logger.warning("Could not load demographics - missing required tables")


    # --- Client Demographics file --->

    # Define the local file path to the Excel file
    file_name = "/code_simulation_3_demographic_data.xlsx"
    file_path = os.getcwd() + file_name

    # Create an empty list to store client data
    list_client = []

    try:
        # Check if the file exists at the specified path
        if os.path.isfile(file_path):
            logger.info(f"Found file at {file_path}. Loading into a Pandas DataFrame...")

            # Load the file into a DataFrame
            client_data = pd.read_excel(
                file_path,
                converters={'username': str, 'uid': str},
                keep_default_na=False
            )

            # Append the DataFrame to the list
            list_client.append(client_data)

            logger.info("File loaded into DataFrame successfully.")
        else:
            logger.error(f"File not found at {file_path}. Please check the file path and try again.")
    except Exception as e:
        logger.error(f"Error reading the file at {file_path}: {e}")

    # Additional processing of `list_client` or any other operations can be added here

    # Print or log the contents of `list_client` for debugging
    if list_client:
        logger.info(f"Data successfully loaded. First 5 rows of the DataFrame:\n{list_client[0].head()}")
    else:
        logger.warning("No data loaded into the list. Check the file path and content.")


    df_client = pd.concat(list_client, ignore_index=True)\
    .assign(
        uid = lambda x: x.apply(lambda y: str(y['User ID']) if pd.notnull(y['User ID']) else None, axis=1),
    )\
    .filter(['uid', 'Region', 'Category', 'Band'])\
    .rename(columns={'Band':'Impact Band'})\
    .assign(
        **{
            #'Impact Band': lambda x: x['Impact Band'].apply(lambda y: 'Indigo' if 'indigo' in y.lower() else y),
            'Impact Band_ord': lambda x: x['Impact Band'].apply(lambda y: 1 if y == 'Red'
                                                                        else 2 if y == 'Orange'
                                                                        else 3 if y == 'Yellow'
                                                                        else 4 if y == 'Green'
                                                                        else 5 if y == 'Blue'
                                                                        else 6 if y == 'Indigo'
                                                                        else None
            ),

            'Region_ord': lambda x: x['Region'].apply(lambda y: 1 if y == 'North America'
                                                                        else 2 if y == 'Europe'
                                                                        else 3 if y == 'AsiaX'
                                                                        else 4 if y == 'Latin America'
                                                                        else 5 if y == 'EEMA'
                                                                        else 6 if y == 'Greater China'
                                                                        else None
            ),

            'Category_ord': lambda x: x['Category'].apply(lambda y: 1 if y == 'Client Service Professionals'
                                                                        else 2 if y == 'Firm Service Professionals'
                                                                        else 3 if y == 'Engagement Service Professionals'
                                                                        else None
            ),
        }
    )

    del list_client

    # Convert 'uid' in both DataFrames to string
    if not df_demog.empty:
        df_demog['uid'] = df_demog['uid'].astype(str)
    df_client['uid'] = df_client['uid'].astype(str)

    df_demog = df_demog\
    .merge(
        df_client,

        how='inner',
        on=['uid']
    )

# <-- Client Demographics file ---


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')

# <----------------------------
# <----- Demographic Data -----
# <----------------------------


# ------------------------------------------->
# ----- Extract sim data from Parquet ------>
# ------------------------------------------->

script_part_n += 1
script_part_c = 'Extracting Data from Parquet (POC)'

print(script_part_n, ':',  script_part_c)
log.info(str(script_part_n) + ':' +  script_part_c)

try:
    # Get EC2 ID for XML file access (still needed for decision levels)
    ec2_id, ec2_region = find_ec2(server)
    logger.info(f"Found EC2 instance: {ec2_id} in region {ec2_region}")

    # Use the new Parquet-based transformation function
    # This replaces: dict_df = extract_data(...)
    dict_df = get_transformed_data_from_parquet(
        pipeline=pipeline,
        sim_ids=sim_id,
        start_date=start_dt,
        end_date=end_dt,
        df_demog=df_demog if not df_demog.empty else None,
        dict_project=dict_project,
        ec2_id=ec2_id,
        ec2_region=ec2_region,
        s3_bucket_name=S3_BUCKET
    )

    print(f"Transformation complete. Generated DataFrames in categories: {list(dict_df.keys())}")
    for category, dfs in dict_df.items():
        if isinstance(dfs, dict):
            print(f"  {category}: {list(dfs.keys())}")

    # Save data.pkl for local development
    try:
        with open('data.pkl', 'wb') as f:
            pickle.dump(dict_df, f)
        logger.info("Saved data.pkl for local development")
    except Exception as e:
        logger.error(f"Failed to save data.pkl: {e}")


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
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
log.info(str(script_part_n) + ':' +  script_part_c)

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
        logger.warning("No survey_responses data available for NPS calculation")


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
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
log.info(str(script_part_n) + ':' +  script_part_c)

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
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')


# <------------------------------
# <----- Change Skill Names -----
# <------------------------------




# Save the Dictionary DataFrames as Gold Tables in S3
logger.info("Saving Gold Tables to S3...")

try:
    for category, content in dict_df.items():
        # Handle nested dictionaries (e.g. 'srv': {'survey_responses': df})
        if isinstance(content, dict):
            for table_key, df in content.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Construct gold table name: gold_{category}_{table_key}
                    gold_table_name = f"gold_{category}_{table_key}"
                    pipeline.write_gold_table(df, gold_table_name)
        
        # Handle direct dataframes (if any exist at top level)
        elif isinstance(content, pd.DataFrame) and not content.empty:
             gold_table_name = f"gold_{category}"
             pipeline.write_gold_table(content, gold_table_name)

    logger.info("✓ All Gold Tables saved to S3")

except Exception as e:
    logger.error(f"Error saving Gold tables: {e}")
    # Don't exit, we still want to try creating the HTML



# ---------------------------->
# ----- Create HTML file ----->
# ---------------------------->




# Remove the 'df_xml' key from the dictionary
if 'sim' in dict_df and 'df_xml' in dict_df['sim']:
    del dict_df['sim']['df_xml']
    print('deleted df_xml')

script_part_n += 1
script_part_c = 'Create HTML file'

print(script_part_n, ':',  script_part_c)
log.info(str(script_part_n) + ':' +  script_part_c)

try:

    index_html = report(
        dict_df,
        dict_project=dict_project,
        start_date=start_dt,
        end_date=end_dt,
        mckinsey=True,
    )

    # Create HTML File (POC output)
    html_output_path = os.path.join(dname, 'index_poc.html')
    with open(html_output_path, 'w') as outfile:
        outfile.write(index_html)
    logger.info(f"Saved POC HTML to {html_output_path}")


except BaseException as e:
    print('***ERROR***: ', str(script_part_n), ':',  script_part_c, ':', str(e))
    log.error('***ERROR***: ' + str(script_part_n) + ': ' + script_part_c + ': ' + str(e))
    sys.exit(str(script_part_n) +  ': ' +  script_part_c + ' ERRORS!')

# <----------------------------
# <----- Create HTML file -----
# <----------------------------




print('Script Duration: ', str(round((timeit.default_timer() - start_tm)/60, 2)), ' minutes')
log.info("Script Duration: " + str(round((timeit.default_timer() - start_tm)/60, 2)) + " minutes")
log.info("<----- SCRIPT RUN SUCCESSFUL -----")
print("<----- SCRIPT RUN SUCCESSFUL -----")
os._exit(os.EX_OK)
