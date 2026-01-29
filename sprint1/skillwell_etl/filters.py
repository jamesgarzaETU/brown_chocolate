
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger('FilterLogic')

def filter_logs_and_users(raw_data, sim_ids, start_date, end_date):
    """
    Standardizes the filtering logic used across all transformations:
    1. Filter out non-learner roles (roleid != 1) from users.
    2. Join logs with valid users.
    3. Calculate 'start_dt' (First Attempt Start Date) for each user/sim.
    4. Filter logs where start_dt >= global start_date.
    5. Filter logs where activity date <= global end_date.

    Returns:
        df_logs_filtered (pd.DataFrame): The filtered logs ready for analysis.
        valid_uids (list): List of userids that passed the filter.
    """
    df_logs = raw_data.get('user_sim_log')
    df_users = raw_data.get('user')
    df_user_group = raw_data.get('user_group') # If needed later for group filtering

    if df_logs is None or df_logs.empty:
        logger.warning("No logs found to filter.")
        return pd.DataFrame(), []

    # 1. Filter Users (Role ID = 1)
    # Equivalent to: WHERE roleid = 1
    if df_users is not None and not df_users.empty and 'roleid' in df_users.columns:
        valid_users = df_users[df_users['roleid'] == 1]['userid'].unique()
        df_logs = df_logs[df_logs['userid'].isin(valid_users)].copy()
    else:
        logger.warning("User table missing or empty. Proceeding without role filter.")
        valid_users = df_logs['userid'].unique()

    # 2. Add 'dt' column
    # SQL: CASE WHEN complete = 1 THEN `end` ELSE `start` END AS dt
    # But wait, logic typically uses start time for 'start_dt' calculation.
    # Let's verify start/end types first.
    if 'start' in df_logs.columns: df_logs['start'] = pd.to_datetime(df_logs['start'])
    if 'end' in df_logs.columns: df_logs['end'] = pd.to_datetime(df_logs['end'])
    
    # Calculate 'dt' for general date comparison
    # Logic: if complete, use end date; else use start date.
    df_logs['dt'] = df_logs['end']
    mask_incomplete = (df_logs['complete'] == 0) | (df_logs['end'].isna())
    df_logs.loc[mask_incomplete, 'dt'] = df_logs.loc[mask_incomplete, 'start']

    # 3. Calculate First Attempt Start Date (start_dt) per Sim/User
    # SQL: MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
    # Note: The SQL groups by simid+userid to find the EARLIEST start date of ANY attempt.
    df_logs['start_date_only'] = df_logs['start'].dt.floor('d') # DATE(start)
    
    # We need to broadcast this minimum back to all rows for that user/sim
    df_logs['first_start_dt'] = df_logs.groupby(['simid', 'userid'])['start_date_only'].transform('min')

    # 4. Filter by Global Date Range
    # SQL: start_dt >= "{2}" (Global Start Date)
    # AND: CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}' (Global End Date)
    
    target_start = pd.to_datetime(start_date).floor('d')
    target_end = pd.to_datetime(end_date).floor('d')

    # Filter 1: The USER'S first attempt must be after the report start date.
    # This excludes users who started the sim purely before the window.
    mask_start = (df_logs['first_start_dt'] >= target_start)

    # Filter 2: The specific log entry must be within the end date.
    # This filters out activity that happened after the report window.
    mask_end = (df_logs['dt'].dt.floor('d') <= target_end)

    # Filter 3: Must be in requested Sims
    mask_sim = df_logs['simid'].isin(sim_ids)

    df_final = df_logs[mask_start & mask_end & mask_sim].copy()

    return df_final, df_final['userid'].unique()
