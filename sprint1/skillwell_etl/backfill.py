
import os
import sys
import json
import pymysql
import argparse
from datetime import datetime
import pandas as pd
import logging
from sshtunnel import SSHTunnelForwarder
import boto3



# Try server path if local import fails
sys.path.append('/home/ubuntu/etu_appliedsciences/_code_libraries/python')
from skillwell_functions import *

# Import from same directory
from .parquet_pipeline import ParquetPipeline

# Credentials
credentials = json.load(open("{}/credentials.json".format('/home/ubuntu/etu_appliedsciences/_credentials'), "r"))



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Backfill')

# Hardcoded Variables
CUSTOMER = 'mckinsey.skillsims.com'
S3_BUCKET = 'etu.appsciences'
CHUNKSIZE = 5000

# Optional: Path to credentials file (can still be overridden or defaults used)
CREDS_FILE = 'credentials.json' # Assumes in current dir or handled by get_db_connection logic

def main():
    # Get RDS ID and Region of Customer database
    db_rds_endpoint, db_rds_port, db_rds_region = find_rds(CUSTOMER)
    print('### db_rds_endpoint:', db_rds_endpoint, '### db_rds_port:', db_rds_port)

    db_user = 'etu_data'
    #db_user = 'root'
    db_name = 'etu_sim'

    # Server and connection settings
    server = 'ochsner.skillsims.com'
    port = 7703

    # 1. Connect to Database
    # --- AWS and Connection Setup ---
    print("--- Setting up AWS connections and credentials ---")

    # (Assume find_rds, find_ec2, and credential loading happen here as before)
    db_rds_endpoint, db_rds_port, db_rds_region = find_rds(CUSTOMER)
    ec2_id, ec2_region = find_ec2(CUSTOMER)

    # Securely fetch the database password from AWS SSM Parameter Store.
    ssm_client = boto3.client('ssm', region_name=db_rds_region)
    response = ssm_client.get_parameter(Name='/appliedscience/mysql-password', WithDecryption=True)
    db_password = response['Parameter']['Value']
    ssm_client.close()

    with sshtunnel(
        ec2_id, credentials,
        remote_address=db_rds_endpoint,
        remote_port=db_rds_port,
        local_port=port
    ) as tunnel:

        print("SSH Tunnel is open.")

        with pymysql.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            user=db_user,
            password=db_password,
            database=db_name
        ) as db_connection:

            # 2. Initialize Pipeline
            pipeline = ParquetPipeline(
                s3_bucket=S3_BUCKET,
                customer=CUSTOMER
            )

            # 3. Define tables to backfill
            # Full list based on user request and proposal
            tables = [
                'user_sim_log',
                'sim_score_log',
                'user_dialogue_log',
                'quiz_question',
                'quiz_answer',
                'quiz_option',
                'simulation',
                'user',
                'language',
                'knowledge_question',
                'knowledge_answer',
                'knowledge_option',
                'score',
                'section',
                'user_group',
                'explore_sim_log'  # Added for practice mode tracking
            ]

            logger.info(f"Starting backfill for {CUSTOMER} to {S3_BUCKET}")
            logger.info(f"Processing {len(tables)} tables with chunksize={CHUNKSIZE}")

            # 4. Run Backfill
            for table in tables:
                try:
                    # Check if table already exists (has metadata)
                    last_update = pipeline.get_last_update_date(table)
                    if last_update:
                        logger.info(f"Skipping backfill for {table}: Already exists (Last update: {last_update}). Run incremental update instead.")
                        continue

                    # Using the pipeline's backfill_table method
                    # We are NOT passing a WHERE clause, so it gets everything (as per "Full Table Storage" proposal)
                    pipeline.backfill_table(
                        table_name=table,
                        db_connection=db_connection,
                        chunksize=CHUNKSIZE
                    )
                except Exception as e:
                    logger.error(f"Failed to backfill {table}: {e}")
                    # Continue to next table instead of crashing entire script
                    continue

if __name__ == '__main__':
    main()