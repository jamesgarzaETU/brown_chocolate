#!/usr/bin/env python3
"""
Parquet Pipeline for ETU Applied Sciences
==========================================

Manages raw MySQL table storage in S3 Parquet format with incremental updates.

This module replaces extract_data() and extract_raw_data() SQL queries with
Parquet-based storage, enabling:
- One-time backfill of all historical data
- Daily incremental updates (append new rows only)
- Fast analytics without hitting MySQL repeatedly

Author: ETU Applied Sciences
Date: 2025-11-20
"""

import pandas as pd
import boto3
import pymysql
import json
import numpy as np
from datetime import datetime, timedelta
import pyarrow.parquet as pq
import pyarrow as pa
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParquetPipeline:
    """
    Manages raw MySQL table storage in S3 Parquet format with incremental updates.

    This class replaces extract_data() and extract_raw_data() SQL queries with
    Parquet-based storage, enabling:
    - One-time backfill of all historical data
    - Daily incremental updates (append new rows only)
    - Fast analytics without hitting MySQL

    Example:
        >>> pipeline = ParquetPipeline(s3_bucket='etu-data-lake', customer='mckinsey')
        >>> pipeline.backfill_all_tables(db_connection, sim_ids=[55, 57])
        >>> pipeline.update_all_tables_incremental(db_connection)
        >>> data = pipeline.load_raw_data_for_analysis(sim_ids=[55, 57])
    """

    def __init__(self, s3_bucket, customer, s3_client=None):
        """
        Initialize the Parquet Pipeline.

        Args:
            s3_bucket (str): S3 bucket name (e.g., 'etu-data-lake')
            customer (str): Customer identifier (e.g., 'mckinsey')
            s3_client (boto3.client, optional): Boto3 S3 client. Creates new if None.
        """
        self.s3_bucket = s3_bucket
        self.customer = customer
        self.s3 = s3_client or boto3.client('s3')

        # Define raw tables path
        self.raw_tables_prefix = f'raw_tables/{customer}/'
        self.gold_tables_prefix = f'gold_tables/{customer}/'
        self.metadata_prefix = f'metadata/{customer}/'

        logger.info(f"Initialized ParquetPipeline for {customer}")
        logger.info(f"  S3 Bucket: {s3_bucket}")
        logger.info(f"  Raw tables path: s3://{s3_bucket}/{self.raw_tables_prefix}")

    # ========================================================================
    # METADATA MANAGEMENT
    # ========================================================================

    def get_last_update_date(self, table_name):
        """
        Get the last update date for a table from S3 metadata.

        Args:
            table_name (str): Table name (e.g., 'user_sim_log')

        Returns:
            str or None: Last update date (YYYY-MM-DD) or None if never updated
        """
        metadata_key = f'{self.metadata_prefix}{table_name}_last_update.txt'

        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=metadata_key)
            last_date = response['Body'].read().decode('utf-8').strip()
            logger.info(f"Last update for {table_name}: {last_date}")
            return last_date
        except self.s3.exceptions.NoSuchKey:
            logger.info(f"No metadata found for {table_name} (first run)")
            return None
        except Exception as e:
            logger.error(f"Error reading metadata for {table_name}: {e}")
            return None

    def update_last_update_date(self, table_name, date):
        """
        Update the last update date for a table in S3 metadata.

        Args:
            table_name (str): Table name
            date (str): Update date (YYYY-MM-DD)
        """
        metadata_key = f'{self.metadata_prefix}{table_name}_last_update.txt'

        try:
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=metadata_key,
                Body=date.encode('utf-8')
            )
            logger.info(f"Updated metadata for {table_name}: {date}")
        except Exception as e:
            logger.error(f"Error updating metadata for {table_name}: {e}")

    def generate_and_save_schema(self, df, table_name, layer='raw'):
        """
        Generate a JSON schema from a DataFrame and save to S3.

        Args:
            df (pd.DataFrame): DataFrame to analyze
            table_name (str): Table name
            layer (str): 'raw' or 'gold' (default: 'raw')
        """
        try:
            schema_data = {
                "table_name": table_name,
                "layer": layer,
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "columns": []
            }

            for col in df.columns:
                dtype = str(df[col].dtype)
                
                # Sample a few non-null values to infer better types if needed (optional enhancement)
                # For now, just map pandas dtypes to generic string descriptions
                
                col_info = {
                    "name": col,
                    "type": dtype,
                    "nullable": bool(df[col].isna().any())
                }
                schema_data["columns"].append(col_info)

            # JSON serialization helper for non-serializable types (like numpy int64)
            def default_converter(o):
                if isinstance(o, (np.int64, np.int32)):
                   return int(o)
                if isinstance(o, (np.float64, np.float32)):
                    return float(o)
                if isinstance(o, (datetime, pd.Timestamp)):
                    return str(o)
                return str(o)

            json_key = f'{self.metadata_prefix}schemas/{layer}_{table_name}.json'
            
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=json_key,
                Body=json.dumps(schema_data, indent=2, default=default_converter)
            )
            
            logger.info(f"  ✓ Saved schema to s3://{self.s3_bucket}/{json_key}")

        except Exception as e:
            logger.error(f"Error generating schema for {table_name}: {e}")
            # Don't raise error, schema generation shouldn't block main pipeline
    
    # ========================================================================
    # PARQUET FILE OPERATIONS
    # ========================================================================

    def write_gold_table(self, df, table_name, compression='snappy'):
        """
        Write a transformed 'Gold' DataFrame to S3 as Parquet.
        
        Args:
            df (pd.DataFrame): DataFrame to save
            table_name (str): Table name (e.g., 'sim_score_summary')
            compression (str): Compression algorithm (default: 'snappy')
        """
        s3_key = f'{self.gold_tables_prefix}{table_name}.parquet'
        s3_path = f's3://{self.s3_bucket}/{s3_key}'

        try:
            logger.info(f"Writing Gold Table: {table_name} ({len(df):,} rows)...")

            df.to_parquet(
                s3_path,
                engine='pyarrow',
                compression=compression,
                index=False
            )
            
            self.generate_and_save_schema(df, table_name, layer='gold')

            logger.info(f"✓ Saved Gold table to {s3_path}")

        except Exception as e:
            logger.error(f"Error writing gold table {table_name}: {e}")
            raise

    def read_parquet_from_s3(self, table_name):
        """
        Read a Parquet file from S3 into a DataFrame.

        Args:
            table_name (str): Table name (e.g., 'user_sim_log')

        Returns:
            pd.DataFrame or None: DataFrame with table data, or None if file doesn't exist
        """
        s3_key = f'{self.raw_tables_prefix}{table_name}.parquet'

        try:
            logger.info(f"Reading {table_name} from S3: s3://{self.s3_bucket}/{s3_key}")

            # Read directly from S3 using pandas
            s3_path = f's3://{self.s3_bucket}/{s3_key}'
            df = pd.read_parquet(s3_path, engine='pyarrow')

            logger.info(f"✓ Loaded {len(df):,} rows from {table_name}")
            return df

        except FileNotFoundError:
            logger.warning(f"File not found: {s3_key} (first run?)")
            return None
        except Exception as e:
            logger.error(f"Error reading {table_name} from S3: {e}")
            return None

    def write_parquet_to_s3(self, df, table_name, compression='snappy'):
        """
        Write a DataFrame to S3 as Parquet.

        Args:
            df (pd.DataFrame): DataFrame to save
            table_name (str): Table name (e.g., 'user_sim_log')
            compression (str): Compression algorithm ('snappy', 'gzip', 'brotli')
        """
        s3_key = f'{self.raw_tables_prefix}{table_name}.parquet'
        s3_path = f's3://{self.s3_bucket}/{s3_key}'

        try:
            logger.info(f"Writing {len(df):,} rows to {table_name}...")

            # Write directly to S3 using pandas
            df.to_parquet(
                s3_path,
                engine='pyarrow',
                compression=compression,
                index=False
            )
            
            # Generate and save schema
            self.generate_and_save_schema(df, table_name, layer='raw')

            logger.info(f"✓ Saved to s3://{self.s3_bucket}/{s3_key}")

        except Exception as e:
            logger.error(f"Error writing {table_name} to S3: {e}")
            raise

    # ========================================================================
    # INITIAL BACKFILL (ONE-TIME)
    # ========================================================================

    def backfill_table(self, table_name, db_connection, where_clause=None, chunksize=10000):
        """
        One-time backfill: Extract entire table from MySQL and save to Parquet.

        Args:
            table_name (str): Table name (e.g., 'user_sim_log')
            db_connection: PyMySQL connection object
            where_clause (str, optional): SQL WHERE clause to filter data (e.g., "WHERE simid IN (55, 57)")
            chunksize (int): Number of rows to process at a time (for large tables)

        Returns:
            pd.DataFrame: The backfilled data

        Example:
            pipeline.backfill_table('user_sim_log', db_connection, where_clause="WHERE simid IN (55, 57)")
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKFILLING TABLE: {table_name}")
        logger.info(f"{'='*60}")

        try:
            # Build SQL query
            if where_clause:
                query = f"SELECT * FROM {table_name} {where_clause}"
            else:
                query = f"SELECT * FROM {table_name}"

            logger.info(f"Query: {query}")

            # Extract data in chunks (for large tables)
            chunks = []
            for chunk in pd.read_sql_query(query, db_connection, chunksize=chunksize):
                chunks.append(chunk)
                logger.info(f"  Loaded chunk: {len(chunk):,} rows")

            # Combine chunks
            df = pd.concat(chunks, ignore_index=True)

            logger.info(f"✓ Extracted {len(df):,} total rows from MySQL")

            # Save to S3 Parquet
            self.write_parquet_to_s3(df, table_name)

            # Update metadata with current date
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.update_last_update_date(table_name, current_date)

            logger.info(f"✓ Backfill complete for {table_name}\n")

            return df

        except Exception as e:
            logger.error(f"Error during backfill of {table_name}: {e}")
            raise

    def backfill_all_tables(self, db_connection, sim_ids=None):
        """
        Backfill all standard ETU tables needed for dashboards.

        Args:
            db_connection: PyMySQL connection object
            sim_ids (list, optional): List of simulation IDs to filter (e.g., [55, 57])

        Returns:
            dict: Dictionary of table_name -> dataframe

        Example:
            pipeline.backfill_all_tables(db_connection, sim_ids=[55, 57])
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKFILLING ALL TABLES FOR {self.customer.upper()}")
        logger.info(f"{'='*60}\n")

        results = {}

        # Define tables to backfill
        # Event tables (filtered by simid if provided)
        if sim_ids:
            where_sim = f"WHERE simid IN ({','.join(map(str, sim_ids))})"
        else:
            where_sim = None

        event_tables = [
            'user_sim_log',
            'sim_score_log',
            'user_dialogue_log',
        ]

        # Quiz tables (need to join through questions)
        quiz_tables = [
            'quiz_question',
            'quiz_answer',
            'quiz_option',
        ]

        # Reference tables (no filter)
        reference_tables = [
            'simulation',
            'user',
            'language',
            'score', 
        ]

        # Backfill event tables
        for table in event_tables:
            results[table] = self.backfill_table(table, db_connection, where_clause=where_sim)

        # Backfill quiz tables (need special handling)
        if sim_ids:
            # First get question IDs for these sims
            df_questions = self.backfill_table('quiz_question', db_connection, where_clause=where_sim)
            results['quiz_question'] = df_questions

            question_ids = df_questions['questionid'].unique()

            # Then get answers and options for those questions
            where_quiz = f"WHERE questionid IN ({','.join(map(str, question_ids))})"
            results['quiz_answer'] = self.backfill_table('quiz_answer', db_connection, where_clause=where_quiz)
            results['quiz_option'] = self.backfill_table('quiz_option', db_connection, where_clause=where_quiz)
        else:
            for table in quiz_tables:
                results[table] = self.backfill_table(table, db_connection)

        # Backfill reference tables
        for table in reference_tables:
            results[table] = self.backfill_table(table, db_connection)

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ ALL TABLES BACKFILLED SUCCESSFULLY")
        logger.info(f"{'='*60}\n")

        return results

    # ========================================================================
    # INCREMENTAL UPDATE (DAILY)
    # ========================================================================

    def update_table_incremental(self, table_name, db_connection, date_column='start'):
        """
        Daily incremental update: Append only new rows to existing Parquet file.

        Args:
            table_name (str): Table name (e.g., 'user_sim_log')
            db_connection: PyMySQL connection object
            date_column (str): Column name to filter by date (default: 'start')

        Returns:
            pd.DataFrame or None: New data that was appended, or None if no new data

        Example:
            new_data = pipeline.update_table_incremental('user_sim_log', db_connection)
        """
        logger.info(f"\n--- Updating {table_name} incrementally ---")

        try:
            # Get last update date
            last_date = self.get_last_update_date(table_name)

            if last_date is None:
                logger.warning(f"No metadata for {table_name}. Run backfill_table() first!")
                return None

            # Calculate date range for new data
            last_date_dt = datetime.strptime(last_date, '%Y-%m-%d')
            today = datetime.now()

            # Query for new data (from last_date + 1 day to today)
            next_date = (last_date_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            today_str = today.strftime('%Y-%m-%d')

            if next_date > today_str:
                logger.info(f"✓ {table_name} is up to date (last update: {last_date})")
                return None

            # Query MySQL for new data
            query = f"""
                SELECT * FROM {table_name}
                WHERE DATE({date_column}) >= '{next_date}'
                  AND DATE({date_column}) <= '{today_str}'
            """

            logger.info(f"Querying new data: {next_date} to {today_str}")
            df_new = pd.read_sql_query(query, db_connection)

            if len(df_new) == 0:
                logger.info(f"✓ No new data for {table_name}")
                self.update_last_update_date(table_name, today_str)
                return None

            logger.info(f"✓ Extracted {len(df_new):,} new rows from MySQL")

            # Read existing Parquet from S3
            df_existing = self.read_parquet_from_s3(table_name)

            if df_existing is None:
                logger.warning(f"Existing parquet not found. Using only new data.")
                df_combined = df_new
            else:
                # Append new data
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                logger.info(f"✓ Combined: {len(df_existing):,} existing + {len(df_new):,} new = {len(df_combined):,} total rows")

            # Save updated Parquet to S3
            self.write_parquet_to_s3(df_combined, table_name)

            # Update metadata
            self.update_last_update_date(table_name, today_str)

            logger.info(f"✓ {table_name} updated successfully\n")

            return df_new

        except Exception as e:
            logger.error(f"Error updating {table_name}: {e}")
            raise

    def update_all_tables_incremental(self, db_connection):
        """
        Update all event tables incrementally (daily run).

        Args:
            db_connection: PyMySQL connection object

        Returns:
            dict: Dictionary of table_name -> new_data_df

        Example:
            updates = pipeline.update_all_tables_incremental(db_connection)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"INCREMENTAL UPDATE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}\n")

        tables_to_update = [
            ('user_sim_log', 'start'),
            ('sim_score_log', 'start'),
            ('user_dialogue_log', 'start'),
        ]

        results = {}

        for table_name, date_col in tables_to_update:
            new_data = self.update_table_incremental(table_name, db_connection, date_column=date_col)
            results[table_name] = new_data

        # Quiz tables need special handling (no date column)
        # For now, we'll re-extract if needed based on new questions
        # This is rare, so we can optimize later

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ INCREMENTAL UPDATE COMPLETE")
        logger.info(f"{'='*60}\n")


        return results

    def update_table_incremental_by_id(self, table_name, db_connection, id_column='id'):
        """
        Incremental update based on Primary Key ID (append new rows where id > max_existing_id).
        Useful for tables without reliable date columns (e.g., sim_score_log).

        Args:
            table_name (str): Table name
            db_connection: PyMySQL connection object
            id_column (str): Primary key column name (default: 'id')

        Returns:
            pd.DataFrame or None: New data that was appended
        """
        logger.info(f"\n--- Updating {table_name} incrementally (by ID: {id_column}) ---")

        try:
            # 1. Read existing parquet to find Max ID
            df_existing = self.read_parquet_from_s3(table_name)

            if df_existing is None or df_existing.empty:
                logger.warning(f"No existing data for {table_name}. Cannot do incremental update by ID.")
                return None

            if id_column not in df_existing.columns:
                 logger.error(f"Column {id_column} not found in existing parquet for {table_name}")
                 return None

            max_id = df_existing[id_column].max()
            logger.info(f"Current Max {id_column}: {max_id}")

            # 2. Query MySQL for rows > max_id
            query = f"SELECT * FROM {table_name} WHERE {id_column} > {max_id}"
            
            logger.info(f"Query: {query}")
            df_new = pd.read_sql_query(query, db_connection)

            if len(df_new) == 0:
                logger.info(f"✓ No new data for {table_name}")
                return None

            logger.info(f"✓ Extracted {len(df_new):,} new rows from MySQL")

            # 3. Append and Write
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            logger.info(f"✓ Combined: {len(df_existing):,} existing + {len(df_new):,} new = {len(df_combined):,} total rows")

            self.write_parquet_to_s3(df_combined, table_name)
            
            # Update metadata date just for reference
            today_str = datetime.now().strftime('%Y-%m-%d')
            self.update_last_update_date(table_name, today_str)

            logger.info(f"✓ {table_name} updated successfully\n")
            return df_new

        except Exception as e:
            logger.error(f"Error updating {table_name} by ID: {e}")
            raise

    # ========================================================================
    # DATA LOADING FOR TRANSFORMATIONS (REPLACES extract_data)
    # ========================================================================

    def load_raw_data_for_analysis(self, sim_ids=None, start_date=None, end_date=None):
        """
        Load raw data from Parquet files for transformation/analysis.
        This replaces the extract_data() function.

        Args:
            sim_ids (list, optional): Filter by simulation IDs (e.g., [55, 57])
            start_date (str, optional): Filter start date (YYYY-MM-DD)
            end_date (str, optional): Filter end date (YYYY-MM-DD)

        Returns:
            dict: Dictionary of table_name -> filtered_df

        Example:
            dict_data = pipeline.load_raw_data_for_analysis(
                sim_ids=[55, 57],
                start_date='2024-11-07',
                end_date='2025-11-19'
            )
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"LOADING RAW DATA FROM PARQUET")
        logger.info(f"Sim IDs: {sim_ids}")
        logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info(f"{'='*60}\n")

        dict_data = {}

        # Define tables to load
        tables_to_load = [
            'user_sim_log',
            'sim_score_log',
            'user_dialogue_log',
            'quiz_question',
            'quiz_answer',
            'quiz_option',
            'simulation',
            'user',
            'language',
            'score',
            'explore_sim_log',  # For practice mode tracking
        ]

        for table_name in tables_to_load:
            logger.info(f"Loading {table_name}...")
            df = self.read_parquet_from_s3(table_name)

            if df is None:
                logger.warning(f"  ⚠ {table_name} not found in S3. Run backfill first!")
                continue

            # Apply filters
            df_filtered = df.copy()

            # Filter by sim_id if applicable and provided
            if sim_ids and 'simid' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['simid'].isin(sim_ids)]
                logger.info(f"  Filtered by simid: {len(df_filtered):,} rows")

            # Filter by date range if applicable and provided
            if start_date and end_date:
                for date_col in ['start', 'end', 'dt']:
                    if date_col in df_filtered.columns:
                        df_filtered[date_col] = pd.to_datetime(df_filtered[date_col])
                        df_filtered = df_filtered[
                            (df_filtered[date_col] >= start_date) &
                            (df_filtered[date_col] <= end_date)
                        ]
                        logger.info(f"  Filtered by {date_col}: {len(df_filtered):,} rows")
                        break

            dict_data[table_name] = df_filtered
            logger.info(f"  ✓ Loaded {len(df_filtered):,} rows\n")

        logger.info(f"{'='*60}")
        logger.info(f"✓ ALL TABLES LOADED FROM PARQUET")
        logger.info(f"{'='*60}\n")

        return dict_data


# ========================================================================
# HELPER FUNCTION: Convert dict_data to format expected by extract_data()
# ========================================================================

def parquet_to_extract_data_format(dict_data):
    """
    Convert raw Parquet data to the format expected by downstream functions.
    This mimics the output structure of extract_raw_data().

    Args:
        dict_data (dict): Dictionary from load_raw_data_for_analysis()

    Returns:
        dict: Formatted dictionary matching extract_raw_data() output
    """
    # The output format is already correct for most use cases
    # Just ensure all expected keys exist

    formatted = {
        'user_sim_log': dict_data.get('user_sim_log', pd.DataFrame()),
        'sim_score_log': dict_data.get('sim_score_log', pd.DataFrame()),
        'user_dialogue_log': dict_data.get('user_dialogue_log', pd.DataFrame()),
        'quiz_question': dict_data.get('quiz_question', pd.DataFrame()),
        'quiz_answer': dict_data.get('quiz_answer', pd.DataFrame()),
        'quiz_option': dict_data.get('quiz_option', pd.DataFrame()),
        'simulation': dict_data.get('simulation', pd.DataFrame()),
        'user': dict_data.get('user', pd.DataFrame()),
        'language': dict_data.get('language', pd.DataFrame()),
    }

    return formatted


# ========================================================================
# CLI INTERFACE (for testing)
# ========================================================================

if __name__ == '__main__':
    """
    Command-line interface for testing the pipeline.

    Usage:
        python parquet_pipeline.py backfill
        python parquet_pipeline.py update
        python parquet_pipeline.py load
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parquet_pipeline.py [backfill|update|load]")
        sys.exit(1)

    command = sys.argv[1]

    # Example configuration
    pipeline = ParquetPipeline(
        s3_bucket='etu-data-lake',
        customer='mckinsey'
    )

    if command == 'backfill':
        print("Backfill command - connect to your database and run:")
        print("  pipeline.backfill_all_tables(db_connection, sim_ids=[55, 57])")

    elif command == 'update':
        print("Update command - connect to your database and run:")
        print("  pipeline.update_all_tables_incremental(db_connection)")

    elif command == 'load':
        print("Loading data from Parquet...")
        data = pipeline.load_raw_data_for_analysis(
            sim_ids=[55, 57],
            start_date='2024-11-07',
            end_date='2025-11-19'
        )
        print(f"\nLoaded {len(data)} tables")
        for table_name, df in data.items():
            print(f"  {table_name}: {len(df):,} rows")

    else:
        print(f"Unknown command: {command}")
        print("Usage: python parquet_pipeline.py [backfill|update|load]")
        sys.exit(1)
