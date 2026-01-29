
import os
import sys
import json
import pymysql
from datetime import datetime
import logging
import boto3
from sshtunnel import SSHTunnelForwarder

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
logger = logging.getLogger('IncrementalUpdate')

# Hardcoded Variables
CUSTOMER = 'mckinsey.skillsims.com'
S3_BUCKET = 'etu.appsciences'

db_primary_keys = {
            'user_sim_log': 'logid',
            'sim_score_log': 'id',
            'user_dialogue_log': 'id',
            'quiz_question': 'questionid',
            'quiz_answer': 'answerid',
            'quiz_option': 'optionid',
            'simulation': 'simid',
            'user': 'userid',
            'language': 'id',
            'knowledge_question': 'questionid',
            'knowledge_answer': 'answerid',
            'knowledge_option': 'optionid',
            'score': 'scoreid',
            'section': 'sectionid',
            'user_group': 'groupid',
            'explore_sim_log': 'logid'  # Added for practice mode tracking
}

def main():
    db_user = 'etu_data'
    #db_user = 'root'
    db_name = 'etu_sim'
    port = 7703

    # --- AWS and Connection Setup ---
    print("--- Setting up AWS connections and credentials ---")

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


            # 3. Tables to update (using db_primary_keys map from global scope)
            # Full list based on user request edit
            
            logger.info(f"Starting incremental update for {CUSTOMER} in {S3_BUCKET}...")

            for table, pk in db_primary_keys.items():
                try:
                    # Use ID-based incremental update
                    pipeline.update_table_incremental_by_id(
                        table_name=table,
                        db_connection=db_connection,
                        id_column=pk
                    )
                except Exception as e:
                    logger.error(f"Failed to update {table}: {e}")
                    
            logger.info("Incremental update process finished.")
        
if __name__ == '__main__':
    main()
