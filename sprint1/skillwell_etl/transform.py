import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import boto3
import time
import re
import html
import xml.etree.ElementTree as ET

# Suppress HuggingFace tokenizer parallelism warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Reduce verbosity of sentence-transformers
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# BERTopic for topic analysis of free-text survey responses
try:
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False

logger = logging.getLogger('TransformData')

from .filters import filter_logs_and_users

def get_skill_baseline(pipeline, raw_data, sim_ids, start_dt, end_dt):
    """
    Calculate skill baseline (First Attempt Scores) from Parquet.
    """
    logger.info("Calculating Skill Baseline...")
    df_logs = raw_data.get('user_sim_log')
    df_scores = raw_data.get('score')
    df_sim_scores = raw_data.get('sim_score_log')
    df_sims = raw_data.get('simulation')
    
    if df_scores is None or df_scores.empty or df_sim_scores is None or df_sim_scores.empty:
        return pd.DataFrame()
         

def get_learner_engagement(df_logs_filtered, df_sims):
    """
    Calculate Learner Engagement stats matching SQL logic:
    Buckets: Not Completed, Completed (>=1), 2+ (>=2), 3+ (>=3), 4+ (>=4)

    SQL Logic (from skillwell_functions.py lines 2007-2015):
    - stat_order 1: n_complete = 0 (Not Completed)
    - stat_order 2: n_complete >= 1 (Completed)
    - stat_order 3: n_complete >= 2 (2 or more)
    - stat_order 4: n_complete >= 3 (3 or more)
    - stat_order 5: n_complete >= 4 (4 or more)

    Total = stat_order 1 + stat_order 2 (Not Completed + Completed with exactly 1)
    """
    logger.info("Calculating Learner Engagement...")
    if df_logs_filtered.empty:
        return pd.DataFrame()

    # Group by simid, userid to get total completions
    # Note: df_logs_filtered already has date filtering applied
    df_user_stats = df_logs_filtered.groupby(['simid', 'userid']).agg({'complete': 'sum'}).reset_index()
    df_user_stats.rename(columns={'complete': 'n_complete'}, inplace=True)

    engagement_results = []

    for simid, group in df_user_stats.groupby('simid'):
        # SQL Logic buckets - CUMULATIVE counts (>= not ==)
        # n_0: exactly 0 completions (Not Completed)
        # n_1+: 1 or more completions (Completed)
        # n_2+: 2 or more completions
        # etc.
        n_0 = len(group[group['n_complete'] == 0])
        n_1_plus = len(group[group['n_complete'] >= 1])  # Completed
        n_2_plus = len(group[group['n_complete'] >= 2])  # 2 or more
        n_3_plus = len(group[group['n_complete'] >= 3])  # 3 or more
        n_4_plus = len(group[group['n_complete'] >= 4])  # 4 or more

        # Total = stat_order 1 + stat_order 2 (from SQL)
        # But SQL stat_order 2 is "Completed" which is n_complete >= 1
        # So total = n_0 + n_1_plus = all users
        total_users = n_0 + n_1_plus

        rows = [
            {'simid': simid, 'stat_order': 1, 'stat': 'Not Completed', 'n': n_0, 'bar_color': '#d3d2d2'},
            {'simid': simid, 'stat_order': 2, 'stat': 'Completed', 'n': n_1_plus, 'bar_color': '#4285f4'},
            {'simid': simid, 'stat_order': 3, 'stat': '2 or more', 'n': n_2_plus, 'bar_color': '#2674f2'},
            {'simid': simid, 'stat_order': 4, 'stat': '3 or more', 'n': n_3_plus, 'bar_color': '#0d5bd9'},
            {'simid': simid, 'stat_order': 5, 'stat': '4 or more', 'n': n_4_plus, 'bar_color': '#0a47a9'},
        ]

        for r in rows:
            r['total'] = total_users
            r['pct'] = (r['n'] / total_users * 100) if total_users > 0 else 0

        engagement_results.extend(rows)

    df_eng = pd.DataFrame(engagement_results)

    if not df_eng.empty and df_sims is not None:
        df_eng = df_eng.merge(df_sims[['simid', 'name']], on='simid', how='left').rename(columns={'name': 'simname'})

    return df_eng

def get_skill_baseline(pipeline, raw_data, sim_ids, start_dt, end_dt):
    """
    Calculate skill baseline (First Attempt Scores) from Parquet.
    Uses filter_logs_and_users for consistent filtering.
    """
    logger.info("Calculating Skill Baseline...")
    df_scores = raw_data.get('score')
    df_sim_scores = raw_data.get('sim_score_log')
    df_sims = raw_data.get('simulation')
    
    if df_scores is None or df_scores.empty or df_sim_scores is None or df_sim_scores.empty:
        return pd.DataFrame()
        
    # 1. Filter Logs & Users (Role=1, First Attempt, Date Range)
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)
    
    if df_logs_filtered.empty:
        return pd.DataFrame()

    # 2. Get First Attempt per Sim/User
    # Note: filter_logs_and_users returns all logs intersecting the window.
    # We specifically want the *first attempt* of the user for baseline.
    # The logic in filter says "user's first attempt must be >= global start".
    # And we filtered out logs > end date.
    
    # Sort to ensure we pick the true first attempt
    df_logs_filtered.sort_values(by=['simid', 'userid', 'end'], ascending=True, inplace=True)
    df_first = df_logs_filtered.drop_duplicates(subset=['simid', 'userid'], keep='first')
    
    # 3. Join with Sim Scores to get values
    
    # 2. Join with Sim Scores to get values
    # sim_score_log usually has logid. join on logid.
    df_values = df_sim_scores.merge(df_first[['logid', 'userid', 'simid']], on=['logid', 'userid', 'simid'], how='inner')
    
    # 3. Join with Score Metadata (to get skill names, bench)
    # score table: simid, scoreid, label (skillname), bench, hidden, orderid
    df_merged = df_values.merge(df_scores, on=['simid', 'scoreid'], how='inner')
    
    # 4. Keep all skills (including hidden) to match show_hidden_skills=True in legacy code
    # The 'hidden' column is preserved in the output

    # 5. Aggregate
    # Avg value per skill per sim
    # Include 'hidden' in groupby to preserve it
    group_cols = ['simid', 'scoreid', 'label', 'orderid']
    if 'hidden' in df_merged.columns:
        group_cols.append('hidden')

    df_agg = df_merged.groupby(group_cols).agg(
        n=('userid', 'nunique'),
        avg_skillscore=('value', 'mean'),
        bench=('bench', 'max') # assuming constant per skill
    ).reset_index()

    df_agg.rename(columns={'label': 'skillname'}, inplace=True)
    df_agg['attempt'] = "First Attempt"
    df_agg['bar_color'] = "#9fdf9f"

    # SQL Logic: CASE WHEN bench > 0 THEN bench END (sets bench to NULL when <= 0)
    df_agg['bench'] = df_agg['bench'].apply(lambda x: x if x > 0 else None)

    # If hidden wasn't in the data, add it as 0 (visible)
    if 'hidden' not in df_agg.columns:
        df_agg['hidden'] = 0

    # Join Sim Name
    if df_sims is not None:
        df_agg = df_agg.merge(df_sims[['simid', 'name']], on='simid', how='left').rename(columns={'name': 'simname'})

    # Remove scoreid to match original schema (scoreid is only used internally for aggregation)
    if 'scoreid' in df_agg.columns:
        df_agg = df_agg.drop(columns=['scoreid'])

    return df_agg

def get_survey_responses(pipeline, raw_data, sim_ids):
    """
    Calculate Survey Responses with specific handling for Types:
    1: Yes/No
    2: Multiple Choice
    4: Free Text
    Uses filter_logs_and_users for valid user population.
    """
    logger.info("Calculating Survey Responses...")
    df_questions = raw_data.get('quiz_question')
    df_answers = raw_data.get('quiz_answer')
    df_options = raw_data.get('quiz_option')
    df_sims = raw_data.get('simulation')
    
    if df_questions is None or df_questions.empty or df_answers is None or df_answers.empty: 
        return pd.DataFrame()

    # 1. Filter Valid Users/Logs FIRST to define the population
    # Note: We need a start/end date for filtering. 
    # The function signature was missing dates in original, but needed for filter!
    # We will assume global dates passed to get_transformed_data are valid.
    # But wait, this function doesn't take date args?
    # I need to update the signature OR pass pre-filtered logs.
    # Let's rely on raw_data having everything, but we need date context.
    # Refactoring decision: pass start/end date to this function too.
    # OR: re-use valid UIDs if we had them. 
    # For now, let's assume we fetch *all* valid responses for the sims.
    # BUT legacy extract_data filters by start_date/end_date.
    # I will update the call site in get_transformed_data first.
    
    # Actually, let's look at get_transformed_data_from_parquet. It has dates.
    # I will stick to the plan and assume I can add dates to args.
    pass 

# RE-WRITING properly with date args.
def get_survey_responses(pipeline, raw_data, sim_ids, start_dt, end_dt):
    logger.info("Calculating Survey Responses...")
    df_questions = raw_data.get('quiz_question')
    df_answers = raw_data.get('quiz_answer')
    df_options = raw_data.get('quiz_option')
    df_sims = raw_data.get('simulation')

    if df_questions is None or df_questions.empty or df_answers is None or df_answers.empty: 
        return pd.DataFrame()

    # 1. Filter Logs & Users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)
    
    if df_logs_filtered.empty:
        return pd.DataFrame()

    # Filter to first completed attempt per user to match SQL logic
    # SQL uses ROW_NUMBER() OVER (... ORDER BY end) ... WHERE rown = 1
    # We filter logs to keep the one with the earliest end date per user/sim
    df_logs_filtered = df_logs_filtered.sort_values(by=['userid', 'simid', 'end'], ascending=True)
    df_logs_filtered = df_logs_filtered.drop_duplicates(subset=['userid', 'simid'], keep='first')

    # Ensure we only include COMPLETED logs (SQL: AND complete = 1)
    if 'complete' in df_logs_filtered.columns:
        if df_logs_filtered['complete'].dtype == object:
             # handle bytes or mixed
             df_logs_filtered = df_logs_filtered[df_logs_filtered['complete'].apply(lambda x: int.from_bytes(x, "big") if isinstance(x, bytes) else int(x)) == 1].copy()
        else:
             df_logs_filtered = df_logs_filtered[df_logs_filtered['complete'] == 1].copy()
        
    valid_log_ids = df_logs_filtered['logid'].unique()
    
    # Filter Answers by Valid Logs
    df_answers_filtered = df_answers[df_answers['logid'].isin(valid_log_ids)].copy()
    
    if df_answers_filtered.empty:
        return pd.DataFrame()

    # Join Answers with Questions
    df_full = df_answers_filtered.merge(df_questions, on='questionid', how='inner')
    
    # Filter by Sim IDs (implicit via logs, but good to ensure question belongs to sim)
    df_full = df_full[df_full['simid'].isin(sim_ids)]

    results = []

    # --- TYPE 1: YES/NO ---
    df_yn = df_full[df_full['typeid'] == 1].copy()
    if not df_yn.empty:
        # Logic: 1 -> Yes (1), 0 -> No (2)
        # SQL: WHEN yesno = 1 THEN 1 WHEN yesno = 0 THEN 2
        
        # Check if 'yesno' exists, else fallback
        if 'yesno' in df_yn.columns:
            df_yn['answerid'] = df_yn['yesno'].apply(lambda x: 1 if x==1 else 2 if x==0 else None)
            df_yn['answer'] = df_yn['yesno'].apply(lambda x: 'Yes' if x==1 else 'No' if x==0 else None)
        else:
            df_yn['answerid'] = 0
            df_yn['answer'] = 'Unknown'
            
        df_yn['optionvalue'] = 0 
        
        # Aggregate
        # Group by simid, orderid, question, answerid, answer
        grp_yn = df_yn.groupby(['simid', 'orderid', 'question', 'answerid', 'answer']).size().reset_index(name='n')
        # Total per question
        grp_yn['total'] = grp_yn.groupby(['simid', 'orderid'])['n'].transform('sum')
        grp_yn['typeid'] = 1
        results.append(grp_yn)

    # --- TYPE 2: MULTIPLE CHOICE ---
    df_mc = df_full[df_full['typeid'] == 2].copy()
    if not df_mc.empty and df_options is not None:
        # Join Options
        df_mc = df_mc.merge(df_options, on='optionid', how='left', suffixes=('', '_opt'))
        
        # SQL: answerid = optionid (Wait, SQL says t_mc_1_2.orderid AS answerid sometimes? Let's check schema. 
        # extract_data line 4128: t_mc_2_2.orderid AS answerid (from quiz_option).
        # Schema for quiz_option has 'orderId' or 'orderid'.
        
        opt_order_col = 'orderid' if 'orderid' in df_options.columns else 'orderId'
        
        df_mc['answerid'] = df_mc[opt_order_col] if opt_order_col in df_mc.columns else df_mc['optionid']
        df_mc['answer'] = df_mc['optiontext']
        df_mc['optionvalue'] = df_mc['value_opt'] if 'value_opt' in df_mc.columns else df_mc['value']
        
        grp_mc = df_mc.groupby(['simid', 'orderid', 'question', 'answerid', 'answer', 'optionvalue']).size().reset_index(name='n')
        grp_mc['total'] = grp_mc.groupby(['simid', 'orderid'])['n'].transform('sum')
        grp_mc['typeid'] = 2
        results.append(grp_mc)

    # --- TYPE 4: FREE TEXT with BERTopic Topic Analysis ---
    # Matches original skillwell_functions.py lines 4592-4724
    df_ft = df_full[df_full['typeid'] == 4].copy()
    if not df_ft.empty:
        # Filter valid text (SQL: LENGTH(TRIM(answer)) >= 4)
        if 'answer' in df_ft.columns:
            df_ft['answer_clean'] = df_ft['answer'].astype(str).str.strip()
            df_ft = df_ft[df_ft['answer_clean'].str.len() >= 4]

            # Get question metadata for topic analysis
            question_meta = df_ft[['simid', 'orderid', 'question']].drop_duplicates()
            if df_sims is not None:
                question_meta = question_meta.merge(df_sims[['simid', 'name']], on='simid', how='left')
                question_meta.rename(columns={'name': 'simname'}, inplace=True)
            else:
                question_meta['simname'] = None

            # Calculate totals per question
            total_counts = df_ft.groupby(['simid', 'orderid']).size().reset_index(name='total')
            question_meta = question_meta.merge(total_counts, on=['simid', 'orderid'], how='left')

            list_topic = []
            list_no_topic = []

            for _, q_row in question_meta.iterrows():
                # Get responses for this question
                q_responses = df_ft[(df_ft['simid'] == q_row['simid']) &
                                   (df_ft['orderid'] == q_row['orderid'])]['answer_clean']

                # Only run BERTopic if > 100 responses (matches original behavior)
                if len(q_responses) > 100 and BERTOPIC_AVAILABLE:
                    logger.info(f"Topic Analysis for {len(q_responses):,} comments (simid={q_row['simid']}, orderid={q_row['orderid']})")

                    try:
                        # Fine-tune topic representations (matches original)
                        representation_model = KeyBERTInspired()
                        topic_model = BERTopic(representation_model=representation_model)

                        topics, probs = topic_model.fit_transform(q_responses)

                        # Get document info and topic info
                        doc_info = topic_model.get_document_info(q_responses)
                        topic_info = topic_model.get_topic_info()

                        # Filter to valid topics (0-49, matches original .query('Topic >= 0 and Topic <= 49'))
                        # This excludes Topic -1 (outliers that don't fit any topic)
                        doc_info = doc_info[doc_info['Topic'].between(0, 49)]
                        topic_info = topic_info[topic_info['Topic'].between(0, 49)]

                        if not doc_info.empty:
                            # Build topic keywords and counts (matches original logic)
                            topic_info['topic_keywords'] = topic_info['Representation'].apply(
                                lambda y: ', '.join([z for z in y if z is not None and z != ""])
                            )
                            topic_info['Count'] = topic_info.groupby('topic_keywords')['Count'].transform('sum')

                            # Create answerid mapping based on topic count ranking
                            answerid_map = topic_info[['topic_keywords', 'Count']].drop_duplicates() \
                                .sort_values('Count', ascending=False) \
                                .reset_index(drop=True)
                            answerid_map['answerid'] = answerid_map.index + 1

                            # Merge topic info with answerid
                            topic_with_answerid = topic_info[['Topic', 'topic_keywords', 'Count']].merge(
                                answerid_map[['topic_keywords', 'answerid']],
                                on='topic_keywords',
                                how='left'
                            )

                            # Merge with document info
                            doc_with_topics = doc_info.merge(
                                topic_with_answerid,
                                on='Topic',
                                how='left'
                            )

                            # Sort and assign optionvalue (row number within each answerid group)
                            doc_with_topics = doc_with_topics.sort_values(['answerid', 'Probability'], ascending=[True, False])
                            doc_with_topics = doc_with_topics[['answerid', 'topic_keywords', 'Document', 'Count']]
                            doc_with_topics.rename(columns={'Document': 'answer', 'Count': 'n'}, inplace=True)

                            # Assign optionvalue (cumcount+1 within answerid group) - matches original line 4652
                            # NOTE: This assigns row numbers 1-20 which affects NPS calculation - see NPS_CALCULATION_BUG.md
                            doc_with_topics['optionvalue'] = doc_with_topics.groupby('answerid')['answer'].cumcount() + 1

                            # Limit to first 20 per topic (matches original .query('optionvalue <= 20'))
                            doc_with_topics = doc_with_topics[doc_with_topics['optionvalue'] <= 20]

                            # Add question metadata
                            doc_with_topics['simid'] = q_row['simid']
                            doc_with_topics['simname'] = q_row['simname']
                            doc_with_topics['orderid'] = q_row['orderid']
                            doc_with_topics['question'] = q_row['question']
                            doc_with_topics['typeid'] = 4
                            doc_with_topics['total'] = q_row['total']
                            doc_with_topics['pct'] = (doc_with_topics['n'] / doc_with_topics['total']) * 100
                            doc_with_topics['bar_color'] = '#e32726'
                            doc_with_topics['topic_analysis'] = 1

                            list_topic.append(doc_with_topics)
                        else:
                            list_no_topic.append({'simid': q_row['simid'], 'orderid': q_row['orderid']})
                    except Exception as e:
                        logger.warning(f"BERTopic failed for simid={q_row['simid']}, orderid={q_row['orderid']}: {e}")
                        list_no_topic.append({'simid': q_row['simid'], 'orderid': q_row['orderid']})
                else:
                    # Less than 100 responses or BERTopic not available - use fallback
                    list_no_topic.append({'simid': q_row['simid'], 'orderid': q_row['orderid']})

            # Combine topic and non-topic results (matches original lines 4676-4723)
            if list_topic and list_no_topic:
                # Questions with topic analysis
                df_topic_results = pd.concat(list_topic, ignore_index=True)

                # Questions without topic analysis - use simple row number assignment
                no_topic_df = pd.DataFrame(list_no_topic)
                df_no_topic = df_ft.merge(no_topic_df, on=['simid', 'orderid'], how='inner')

                # Process non-topic questions with simple grouping
                # NOTE: For non-BERTopic questions, n should be null (like original SQL sets ,null AS n)
                grp_no_topic = df_no_topic.groupby(['simid', 'orderid', 'question', 'answer_clean']).size().reset_index(name='response_count')
                grp_no_topic.rename(columns={'answer_clean': 'answer'}, inplace=True)
                grp_no_topic = grp_no_topic.merge(total_counts, on=['simid', 'orderid'], how='left')
                grp_no_topic = grp_no_topic.sort_values(['simid', 'orderid', 'response_count'], ascending=[True, True, False])
                grp_no_topic['optionvalue'] = grp_no_topic.groupby(['simid', 'orderid']).cumcount() + 1
                grp_no_topic = grp_no_topic[grp_no_topic['optionvalue'] <= 20]
                grp_no_topic['n'] = np.nan  # Original SQL sets n=null for free-text without topic analysis
                grp_no_topic['answerid'] = 0
                grp_no_topic['typeid'] = 4
                grp_no_topic['topic_analysis'] = 0
                grp_no_topic['topic_keywords'] = None
                grp_no_topic['bar_color'] = None
                if df_sims is not None:
                    grp_no_topic = grp_no_topic.merge(df_sims[['simid', 'name']], on='simid', how='left')
                    grp_no_topic.rename(columns={'name': 'simname'}, inplace=True)

                # Combine both
                grp_ft = pd.concat([df_topic_results, grp_no_topic], ignore_index=True)
                results.append(grp_ft)

            elif list_topic:
                # Only topic analysis results
                grp_ft = pd.concat(list_topic, ignore_index=True)
                results.append(grp_ft)

            elif list_no_topic:
                # Only non-topic results - use fallback simple processing
                # NOTE: For non-BERTopic questions, n should be null (like original SQL sets ,null AS n)
                grp_ft = df_ft.groupby(['simid', 'orderid', 'question', 'answer_clean']).size().reset_index(name='response_count')
                grp_ft.rename(columns={'answer_clean': 'answer'}, inplace=True)
                grp_ft = grp_ft.merge(total_counts, on=['simid', 'orderid'], how='left')
                grp_ft = grp_ft.sort_values(['simid', 'orderid', 'response_count'], ascending=[True, True, False])
                grp_ft['optionvalue'] = grp_ft.groupby(['simid', 'orderid']).cumcount() + 1
                grp_ft = grp_ft[grp_ft['optionvalue'] <= 20]
                grp_ft['n'] = np.nan  # Original SQL sets n=null for free-text without topic analysis
                grp_ft['answerid'] = 0
                grp_ft['typeid'] = 4
                grp_ft['topic_analysis'] = 0
                grp_ft['topic_keywords'] = None
                results.append(grp_ft)

    if not results:
        return pd.DataFrame()

    df_final = pd.concat(results, ignore_index=True)

    # Convert total to float64 to match original SQL output
    df_final['total'] = df_final['total'].astype('float64')

    # Only recalculate pct if not already set (BERTopic results have pct set)
    if 'pct' not in df_final.columns:
        df_final['pct'] = (df_final['n'] / df_final['total'] * 100).fillna(0)
    else:
        # Fill any missing pct values
        df_final['pct'] = df_final['pct'].fillna((df_final['n'] / df_final['total'] * 100).fillna(0))

    # Set bar_color for non-free-text if not already set
    if 'bar_color' not in df_final.columns:
        df_final['bar_color'] = None
    else:
        df_final['bar_color'] = df_final['bar_color'].where(df_final['bar_color'].notna(), None)

    # Add missing columns expected by reference format
    # Use pd.NaT for datetime and np.nan for numeric to match original data types
    df_final['dt'] = pd.NaT  # Date column - typically null for survey responses (datetime64[ns])
    df_final['scale_type'] = None  # Scale type for rating questions

    # topic_analysis and topic_keywords - preserve BERTopic values, default others to NaN/None
    if 'topic_analysis' not in df_final.columns:
        df_final['topic_analysis'] = np.nan
    else:
        # Convert topic_analysis to float64 for consistency (1.0 for topic, 0.0 for non-topic, NaN for other types)
        df_final['topic_analysis'] = df_final['topic_analysis'].astype('float64')

    if 'topic_keywords' not in df_final.columns:
        df_final['topic_keywords'] = None

    # Merge simname - either add column if missing, or fill in null values
    if df_sims is not None:
        if 'simname' not in df_final.columns:
            df_final = df_final.merge(df_sims[['simid', 'name']], on='simid', how='left').rename(columns={'name': 'simname'})
        else:
            # Fill in null simname values from simulation table
            simname_map = df_sims.set_index('simid')['name'].to_dict()
            df_final['simname'] = df_final.apply(
                lambda row: simname_map.get(row['simid']) if pd.isna(row['simname']) else row['simname'],
                axis=1
            )

    return df_final


def get_time_spent(pipeline, raw_data, sim_ids, start_dt, end_dt):
    """
    Calculate time spent distribution by attempt number.
    Converts SQL from skillwell_functions.py lines 3518-3686.

    Uses MEDIAN cumulative duration (not mean) to match legacy behavior.
    Legacy SQL uses ROW_NUMBER to find median rows.

    Returns DataFrame with columns:
    - simid, simname
    - stat_order, stat (e.g., "All Attempts<br>(N Learners)")
    - bar_color
    - n (count of users)
    - total (total users)
    - pct (percentage)
    - avg_cum_duration (median cumulative duration in minutes)
    - opac (opacity for visualization)
    """
    logger.info("Calculating Time Spent...")

    # 1. Get filtered logs and valid users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    if df_logs_filtered.empty:
        return pd.DataFrame()

    # Helper to convert bytes to int (for complete column)
    def convert_bit(x):
        if isinstance(x, bytes):
            return int.from_bytes(x, "big")
        try:
            return int(x)
        except:
            return 0

    # 2. Apply complete conversion if needed (bytes vs int)
    if df_logs_filtered['complete'].dtype == object:
        complete_mask = df_logs_filtered['complete'].apply(convert_bit) == 1
    else:
        complete_mask = df_logs_filtered['complete'] == 1

    # 3. Filter completed attempts only
    df_completed = df_logs_filtered[complete_mask].copy()

    if df_completed.empty:
        return pd.DataFrame()

    # 4. Use duration column from database (in seconds), convert to minutes
    # Legacy SQL: duration/60 AS duration
    if 'duration' in df_completed.columns:
        df_completed['duration_min'] = df_completed['duration'] / 60
    else:
        # Fallback to calculating from start/end
        df_completed['duration_min'] = (
            (pd.to_datetime(df_completed['end']) - pd.to_datetime(df_completed['start']))
            .dt.total_seconds() / 60
        )

    # 5. Add attempt number and cumulative duration per user
    # Legacy SQL: ROW_NUMBER() OVER (PARTITION BY simid, userid ORDER BY `end`) AS attempt
    #             SUM(duration/60) OVER (PARTITION BY simid, userid ORDER BY `end`) AS cum_duration
    df_completed = df_completed.sort_values(['simid', 'userid', 'end'])
    df_completed['attempt'] = df_completed.groupby(['simid', 'userid']).cumcount() + 1
    df_completed['cum_duration'] = df_completed.groupby(['simid', 'userid'])['duration_min'].cumsum()

    # Mark last row per user (for "All Attempts" stat)
    # Legacy SQL: ROW_NUMBER() OVER (PARTITION BY simid, userid ORDER BY `end` DESC) AS last_row
    df_completed['last_row'] = df_completed.groupby(['simid', 'userid']).cumcount(ascending=False) == 0

    # 6. Get simnames for all sims
    df_sims = raw_data.get('simulation')
    sim_names = {}
    if df_sims is not None:
        for _, row in df_sims[df_sims['simid'].isin(sim_ids)].iterrows():
            sim_names[row['simid']] = row['name'].strip() if isinstance(row['name'], str) else row['name']

    # 7. Define stat categories (always include all 5)
    stat_definitions = [
        (1, 'All Attempts', '#1f77b4'),
        (2, '1 Attempt', '#e32726'),
        (3, '2 Attempts', '#e32726'),
        (4, '3 Attempts', '#e32726'),
        (5, '4+ Attempts', '#e32726'),
    ]

    # 8. Calculate stats for each sim
    results = []

    for simid in sim_ids:
        df_sim = df_completed[df_completed['simid'] == simid]
        simname = sim_names.get(simid, f'Sim {simid}')

        # Calculate total users (from "All Attempts" - users with last_row)
        df_all = df_sim[df_sim['last_row'] == True]
        total_users = len(df_all) if not df_all.empty else 0

        for stat_order, stat_base, bar_color in stat_definitions:
            if stat_order == 1:
                # All Attempts: last attempt per user (cumulative duration)
                df_stat = df_all
            elif stat_order == 2:
                # 1 Attempt: first attempt for each user
                df_stat = df_sim[df_sim['attempt'] == 1]
            elif stat_order == 3:
                # 2 Attempts: second attempt for each user
                df_stat = df_sim[df_sim['attempt'] == 2]
            elif stat_order == 4:
                # 3 Attempts: third attempt for each user
                df_stat = df_sim[df_sim['attempt'] == 3]
            else:
                # 4+ Attempts: users with 4+ attempts (last row only)
                df_stat = df_sim[(df_sim['attempt'] >= 4) & (df_sim['last_row'] == True)]

            n = len(df_stat) if not df_stat.empty else 0

            # Calculate median cumulative duration (legacy uses median via ROW_NUMBER trick)
            if n > 0:
                median_cum = df_stat['cum_duration'].median()
            else:
                median_cum = 0.0

            # Format stat label with learner count (legacy format)
            learner_word = "Learner" if n == 1 else "Learners"
            stat_label = f"{stat_base}<br>({n:,} {learner_word})"

            # Calculate percentage
            pct = (n / total_users * 100) if total_users > 0 else 0.0

            # Calculate opacity (legacy formula)
            # CASE WHEN total > 0 THEN (((((n/total)*100) - 0)/(100 - 0))*(1.0 - 0.1))+0.1 ELSE 1 END
            if total_users > 0:
                opac = (((pct - 0) / (100 - 0)) * (1.0 - 0.1)) + 0.1
            else:
                opac = 1.0

            results.append({
                'simid': simid,
                'simname': simname,
                'total': total_users,
                'stat_order': stat_order,
                'stat': stat_label,
                'bar_color': bar_color,
                'n': n,
                'pct': pct,
                'avg_cum_duration': median_cum,
                'opac': opac,
            })

    if not results:
        return pd.DataFrame()

    df_time_spent = pd.DataFrame(results)

    # 9. Sort by simid and stat_order
    df_time_spent.sort_values(['simid', 'stat_order'], inplace=True)

    logger.info(f"✓ Time spent complete: {len(df_time_spent)} rows")
    return df_time_spent


def get_practice_mode(pipeline, raw_data, sim_ids, start_dt, end_dt):
    """
    Calculate practice mode usage statistics.
    Converts SQL from skillwell_functions.py lines 3699-3867.

    Uses explore_sim_log to determine if a user practiced before assessing.
    A user is considered to have "practiced" if they have entries in explore_sim_log.

    Returns DataFrame with columns:
    - simid, simname
    - total (total users who completed)
    - n (number who practiced before assessing)
    - pct (percentage who practiced)
    - avg_practice_duration (average practice duration in minutes)
    """
    logger.info("Calculating Practice Mode...")

    # 1. Get filtered logs and valid users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    if df_logs_filtered.empty:
        return pd.DataFrame()

    # Helper to convert bytes to int
    def convert_bit(x):
        if isinstance(x, bytes):
            return int.from_bytes(x, "big")
        try:
            return int(x)
        except:
            return 0

    # 2. Apply complete conversion if needed (bytes vs int)
    if df_logs_filtered['complete'].dtype == object:
        complete_mask = df_logs_filtered['complete'].apply(convert_bit) == 1
    else:
        complete_mask = df_logs_filtered['complete'] == 1

    # 3. Filter completed attempts
    df_completed = df_logs_filtered[complete_mask].copy()

    if df_completed.empty:
        # Return sims with 0 practice
        df_sims = raw_data.get('simulation')
        if df_sims is not None:
            df_result = df_sims[df_sims['simid'].isin(sim_ids)][['simid', 'name']].copy()
            df_result.rename(columns={'name': 'simname'}, inplace=True)
            df_result['total'] = 0
            df_result['n'] = 0
            df_result['pct'] = 0.0
            df_result['avg_practice_duration'] = 0.0
            return df_result
        return pd.DataFrame()

    # 4. Get explore_sim_log for practice tracking (from raw_data loaded via parquet)
    df_explore = raw_data.get('explore_sim_log')

    if df_explore is None or df_explore.empty:
        logger.warning("No explore_sim_log data available - practice tracking will show 0")
        # Return with 0 practice
        df_sims = raw_data.get('simulation')
        results = []
        for simid in sim_ids:
            df_sim = df_completed[df_completed['simid'] == simid]
            if df_sim.empty:
                continue
            total = df_sim['userid'].nunique()
            results.append({
                'simid': simid,
                'total': total,
                'n': 0,
                'pct': 0.0,
                'avg_practice_duration': 0.0
            })
        if not results:
            return pd.DataFrame()
        df_practice = pd.DataFrame(results)
        if df_sims is not None:
            df_practice = df_practice.merge(df_sims[['simid', 'name']], on='simid', how='left')
            df_practice.rename(columns={'name': 'simname'}, inplace=True)
        return df_practice

    # 5. Filter explore_sim_log for relevant sims
    df_explore_filtered = df_explore[df_explore['simid'].isin(sim_ids)].copy()

    # 6. Calculate practice duration per user per sim from explore_sim_log
    # Legacy SQL: SELECT simid, userid, SUM(duration/60) AS duration FROM explore_sim_log
    df_practice_duration = df_explore_filtered.groupby(['simid', 'userid']).agg(
        duration=('duration', lambda x: x.sum() / 60)  # Convert to minutes
    ).reset_index()

    # 7. Get unique users who completed each sim
    df_completed_users = df_completed.groupby(['simid', 'userid']).agg(
        start_dt=('start', 'min')
    ).reset_index()

    # 8. LEFT JOIN completed users with practice duration
    # A user "practiced" if they have a record in explore_sim_log
    df_merged = df_completed_users.merge(
        df_practice_duration,
        on=['simid', 'userid'],
        how='left'
    )
    df_merged['practiced'] = df_merged['duration'].notna().astype(int)

    # 9. Aggregate per sim
    results = []
    for simid in sim_ids:
        df_sim = df_merged[df_merged['simid'] == simid]

        if df_sim.empty:
            continue

        total = len(df_sim)
        n_practiced = df_sim['practiced'].sum()
        pct = (n_practiced / total * 100) if total > 0 else 0

        # Calculate median practice duration (legacy uses median via ROW_NUMBER trick)
        practice_durations = df_sim[df_sim['practiced'] == 1]['duration']
        if len(practice_durations) > 0:
            avg_practice_duration = practice_durations.median()
        else:
            avg_practice_duration = 0.0

        results.append({
            'simid': simid,
            'total': total,
            'n': int(n_practiced),
            'pct': pct,
            'avg_practice_duration': avg_practice_duration if pd.notna(avg_practice_duration) else 0.0
        })

    if not results:
        return pd.DataFrame()

    df_practice = pd.DataFrame(results)

    # 10. Add simname
    df_sims = raw_data.get('simulation')
    if df_sims is not None:
        df_practice = df_practice.merge(df_sims[['simid', 'name']], on='simid', how='left')
        df_practice.rename(columns={'name': 'simname'}, inplace=True)

    logger.info(f"✓ Practice mode complete: {len(df_practice)} sims")
    return df_practice


def get_skill_improvement(pipeline, raw_data, sim_ids, start_dt, end_dt, show_hidden_skills=True):
    """
    Calculate skill improvement between first and last attempt.
    Converts SQL from skillwell_functions.py lines 2623-2743.

    Returns DataFrame with columns:
    - simid, simname
    - orderid, skillname
    - bench (benchmark score)
    - hidden (0 or 1)
    - attempt ("First Attempt" or "Last Attempt")
    - bar_color
    - n (number of users)
    - avg_skillscore (average score)
    - avg_chg_skillscore (average change from first to last)
    """
    logger.info("Calculating Skill Improvement...")

    df_scores = raw_data.get('score')
    df_sim_scores = raw_data.get('sim_score_log')
    df_sims = raw_data.get('simulation')

    if df_scores is None or df_scores.empty or df_sim_scores is None or df_sim_scores.empty:
        return pd.DataFrame()

    # 1. Get filtered logs and valid users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    if df_logs_filtered.empty:
        return pd.DataFrame()

    # 2. Filter to users with multiple attempts
    df_logs_completed = df_logs_filtered[df_logs_filtered['complete'] == 1].copy()
    user_attempt_counts = df_logs_completed.groupby(['simid', 'userid']).size()
    users_with_multiple_attempts = user_attempt_counts[user_attempt_counts > 1].index

    if len(users_with_multiple_attempts) == 0:
        return pd.DataFrame()

    # Filter to only users with multiple attempts
    df_multi = df_logs_completed[
        df_logs_completed.set_index(['simid', 'userid']).index.isin(users_with_multiple_attempts)
    ].copy()

    # 3. Mark first and last attempts
    df_multi = df_multi.sort_values(['simid', 'userid', 'end'])
    df_multi['attempt_num'] = df_multi.groupby(['simid', 'userid']).cumcount() + 1
    df_multi['last_attempt_num'] = df_multi.groupby(['simid', 'userid']).cumcount(ascending=False) + 1

    df_multi['attempt'] = df_multi.apply(
        lambda row: 'First Attempt' if row['attempt_num'] == 1
                   else 'Last Attempt' if row['last_attempt_num'] == 1
                   else None,
        axis=1
    )

    df_multi = df_multi[df_multi['attempt'].notnull()]

    # 4. Join with sim_score_log
    df_with_scores = df_multi.merge(
        df_sim_scores[['simid', 'userid', 'logid', 'scoreid', 'value']],
        on=['simid', 'userid', 'logid'],
        how='inner'
    )

    df_with_scores.rename(columns={'value': 'skillscore'}, inplace=True)

    # 5. Join with score metadata
    df_with_scores = df_with_scores.merge(
        df_scores[['simid', 'scoreid', 'orderid', 'label', 'bench', 'hidden']],
        on=['simid', 'scoreid'],
        how='inner'
    )

    df_with_scores.rename(columns={'label': 'skillname'}, inplace=True)

    # 6. Filter hidden skills if needed
    if not show_hidden_skills and 'hidden' in df_with_scores.columns:
        df_with_scores = df_with_scores[df_with_scores['hidden'] == 0]

    # 7. Calculate improvement (lag score for comparison)
    df_with_scores = df_with_scores.sort_values(['simid', 'userid', 'scoreid', 'attempt_num'])
    df_with_scores['lag_skillscore'] = df_with_scores.groupby(['simid', 'userid', 'scoreid'])['skillscore'].shift(1)

    # 8. Aggregate
    df_agg = df_with_scores.groupby(['simid', 'orderid', 'skillname', 'bench', 'hidden', 'attempt']).agg(
        n=('userid', 'nunique'),
        avg_skillscore=('skillscore', 'mean'),
        avg_chg_skillscore=('lag_skillscore', lambda x: (df_with_scores.loc[x.index, 'skillscore'] - x).mean())
    ).reset_index()

    # 9. Add bar colors
    df_agg['bar_color'] = df_agg['attempt'].map({
        'First Attempt': '#9fdf9f',
        'Last Attempt': '#339933'
    })

    # SQL Logic: CASE WHEN bench > 0 THEN bench END (sets bench to NULL when <= 0)
    df_agg['bench'] = df_agg['bench'].apply(lambda x: x if x > 0 else None)

    # 10. Add simname
    if df_sims is not None:
        df_agg = df_agg.merge(df_sims[['simid', 'name']], on='simid', how='left')
        df_agg.rename(columns={'name': 'simname'}, inplace=True)

    # 11. Sort
    df_agg.sort_values(['simid', 'orderid', 'attempt'], inplace=True)

    return df_agg


def get_learner_engagement_over_time(pipeline, raw_data, sim_ids, start_dt, end_dt):
    """
    Calculate learner engagement over time (separate from proj version).
    Converts SQL from skillwell_functions.py lines 2036-2161.

    Returns DataFrame similar to proj_engagement_over_time but per sim.
    """
    logger.info("Calculating Learner Engagement Over Time...")

    # 1. Get filtered logs and valid users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    if df_logs_filtered.empty:
        return pd.DataFrame()

    # 2. Filter completed attempts
    # Handle bytes type for complete column (stored as b'\x01' or b'\x00' in parquet)
    if df_logs_filtered['complete'].dtype == object:
        complete_mask = df_logs_filtered['complete'].apply(
            lambda x: int.from_bytes(x, "big") if isinstance(x, bytes) else int(x) if pd.notnull(x) else 0
        ) == 1
    else:
        complete_mask = df_logs_filtered['complete'] == 1
    df_completed = df_logs_filtered[complete_mask].copy()

    if df_completed.empty:
        return pd.DataFrame()

    # 3. Determine time frequency
    period_days = (end_dt - start_dt).days + 1
    freq_period = 'D' if period_days <= 30 else 'W' if period_days <= 112 else 'M' if period_days <= 730 else 'Q'
    freq_offset = 'D' if period_days <= 30 else 'W' if period_days <= 112 else 'MS' if period_days <= 730 else 'QS'

    # 4. Generate complete date range for all periods between start_dt and end_dt
    # This matches the SQL behavior which generates all periods even with n=0
    # Normalize start_dt to the beginning of the period to include the first partial period
    if freq_period == 'M':
        period_start = pd.Timestamp(start_dt).to_period('M').to_timestamp()
    elif freq_period == 'Q':
        period_start = pd.Timestamp(start_dt).to_period('Q').to_timestamp()
    elif freq_period == 'W':
        # Align to Monday of the week
        period_start = pd.Timestamp(start_dt) - pd.Timedelta(days=pd.Timestamp(start_dt).dayofweek)
    else:  # 'D'
        period_start = pd.Timestamp(start_dt)

    all_periods = pd.date_range(start=period_start, end=end_dt, freq=freq_offset)

    # Get unique simids from the data
    simids_in_data = df_completed['simid'].unique()

    # Create a complete grid of simid x period combinations
    df_grid = pd.DataFrame([(sid, dt) for sid in simids_in_data for dt in all_periods],
                           columns=['simid', 'dt'])

    # 5. Group completed data by time period (using first day of period)
    df_completed['dt'] = pd.to_datetime(df_completed['end']).dt.to_period(freq_period).dt.to_timestamp()

    # Aggregate by simid and dt
    df_agg = df_completed.groupby(['simid', 'dt'])['userid'].nunique().reset_index(name='n')

    # 6. Left join grid with aggregated data to include periods with n=0
    df_time = df_grid.merge(df_agg, on=['simid', 'dt'], how='left')
    df_time['n'] = df_time['n'].fillna(0).astype(int)

    # Sort by simid and dt
    df_time = df_time.sort_values(['simid', 'dt']).reset_index(drop=True)

    # 7. Calculate cumulative (use float64 to match original SQL output)
    df_time['n_cum'] = df_time.groupby('simid')['n'].cumsum().astype('float64')

    # 8. Calculate totals and percentages
    df_totals = df_time.groupby('simid')['n'].sum().reset_index(name='total')
    df_time = df_time.merge(df_totals, on='simid')
    df_time['pct'] = (df_time['n'] / df_time['total'] * 100).fillna(0)

    # 9. Add metadata
    df_time['time_freq'] = freq_period.lower()
    df_time['bar_color'] = '#4285f4'

    # 10. Add simname
    df_sims = raw_data.get('simulation')
    if df_sims is not None:
        df_time = df_time.merge(df_sims[['simid', 'name']], on='simid', how='left')
        df_time.rename(columns={'name': 'simname'}, inplace=True)

    # 11. Convert dt to string (object type) to match original SQL output format
    df_time['dt'] = df_time['dt'].dt.strftime('%Y-%m-%d')

    return df_time


# ================================================================
# HELPER FUNCTIONS FOR DECISION LEVELS
# ================================================================

def stringcleaner(x):
    """
    Cleans a given string by removing carriage return characters, stripping leading and trailing whitespace,
    and ensuring proper encoding and decoding.

    Args:
        x (str): The input string to be cleaned.

    Returns:
        str: The cleaned string after removing carriage return characters, trimming whitespace, and ensuring UTF-8 encoding.
    """
    # Replace carriage return characters with a space and strip leading/trailing spaces
    clean = x.replace("\r", " ").strip()

    # Ensure the string is properly encoded to UTF-8 and then decoded
    clean = clean.encode("utf-8").decode()

    return clean


def xml_to_df(file, split_score=False):
    """
    Converts an XML file (simulation structure) into a pandas DataFrame.

    Args:
        file (str): XML content as string
        split_score (bool): Whether to split scores into separate rows

    Returns:
        pd.DataFrame: Parsed XML data with simulation structure
    """
    performancebranch_ids = []
    list_xml = []

    root = ET.fromstring(file)
    if root.find('./scenario/info/description/simulation/name') is not None:
        simname = root.find('./scenario/info/description/simulation/name').text
    if root.find('./scenario/info/description/name') is not None:
        simname = root.find('./scenario/info/description/name').text

    # Sections
    attrib_name = 'refId'
    dictSection = {}
    dictSectionInverse = {}
    for sec in root.find('./scenario/info/description/sections'):
        if sec.find("./refId") is not None:
            dictSection[int(sec.find("./refId").text)] = sec.find("./name").text
            dictSectionInverse[sec.find("./name").text] = int(sec.find("./refId").text)
        elif sec.find("./ref") is not None:
            attrib_name = 'ref'
            dictSection[sec.find("./id").text] = int(sec.find("./ref").text)
            dictSectionInverse[int(sec.find("./ref").text)] = sec.find("./id").text

    for element in root.findall(".//element"):
        id = element.attrib["id"]
        x_loc = int(element.attrib["x"])
        y_loc = int(element.attrib["y"])

        choice = re.sub(r'<[^>]*>', '', element.find("./dialog/statement").text.replace('<br />', '?br?').replace('<br>', '?br?')).replace('?br?', '<br>') if element.find("./dialog/statement").text is not None else None
        choice = html.unescape(choice).replace(u'\xa0', u' ').replace(u'\r', '') if choice is not None else None
        choice = stringcleaner(choice) if choice is not None else None

        result = re.sub(r'<[^>]*>', '', element.find("./dialog/response").text.replace('<br />', '?br?').replace('<br>', '?br?')).replace('?br?', '<br>') if element.find("./dialog/response").text is not None else None
        result = html.unescape(result).replace(u'\xa0', u' ').replace(u'\r', '') if result is not None else None
        result = stringcleaner(result) if result is not None else None

        practice_coach = element.find("./dialog/coach")
        if practice_coach is not None:
            coaching = re.sub(r'<[^>]*>', '', practice_coach.text.replace('<br />', '?br?').replace('<br>', '?br?')).replace('?br?', '<br>') if practice_coach.text is not None else None
            coaching = html.unescape(coaching).replace(u'\xa0', u' ').replace(u'\r', '') if coaching is not None else None
            coaching = stringcleaner(coaching) if coaching is not None else None
        else:
            coaching = None

        sectionid = None
        if len(dictSection) == 0 or attrib_name == 'ref':
            if 'refId' in element.find("./dialog/sections/section").attrib.keys():
                section = element.find("./dialog/sections/section").attrib['refId']
                if section:
                    sectionid = int(section)
                    section = stringcleaner( dictSectionInverse.get(int(section)) )
            else:
                section = element.find("./dialog/sections/section").text
                if section:
                    sectionid = dictSection.get(section)
                    section = stringcleaner(section)
        else:
            section = element.find("./dialog/sections/section").attrib['refId']
            if section:
                sectionid = int(section)
                section = stringcleaner(dictSection.get(int(section)))

        section = html.unescape(section).replace(u'\xa0', u' ').replace(u'\r', '').replace(u'\n', '') if section is not None else None
        section = stringcleaner(section) if section is not None else None

        performancebranch = element.find("./adaptivity/triggers/performancebranch")
        if performancebranch is not None:
            performancebranch_ids.append(id)

        scoring = root.findall(".//*[@ref='{}']".format(id))
        for score_ in scoring:
            startingpoint = None
            qtype = None
            feedback = None
            behaviorid = None
            behavior = None
            consequence = None
            skillid = []
            skillname = []
            skillscore = []

            if score_ != None:
                try:
                    startingpoint = score_.attrib["id"].split("-")[0]
                    qtype = score_.find("./type").text
                    feedback = score_.find("./coach").text
                    feedback = re.sub(r'<[^>]*>', '', feedback.replace('<br>', '?br?')).replace('?br?', '<br>') if feedback is not None else None
                    feedback = html.unescape(feedback).replace(u'\xa0', u' ').replace(u'\r', '') if feedback is not None else None
                    feedback = stringcleaner(feedback) if feedback is not None else None

                    behavior = score_.find("./behavior")
                    if behavior is not None:
                        behaviorid = behavior.attrib['refId']
                        behavior = stringcleaner(behavior.text)
                        behavior = html.unescape(behavior).replace(u'\xa0', u' ').replace(u'\r', '').replace(u'\n', '') if behavior is not None else None

                    consequence = score_.find("./consequence")
                    if consequence is not None:
                        consequence = stringcleaner(consequence.text)
                        consequence = html.unescape(consequence).replace(u'\xa0', u' ').replace(u'\r', '').replace(u'\n', '') if consequence is not None else None

                    for score in score_.findall("./skill/score"):
                        if score.attrib["refId"] is not None:
                            skillid.append(int(score.attrib["refId"]))
                        else:
                            skillid.append(score.attrib["refId"])

                        this_skillname = score.attrib["label"].strip().replace('\u200b', '')
                        this_skillname = re.sub(r'<[^>]*>', '', this_skillname.replace('<br>', '?br?')).replace('?br?', '<br>') if this_skillname is not None else None
                        this_skillname = html.unescape(this_skillname).replace(u'\xa0', u' ').replace(u'\r', '') if this_skillname is not None else None
                        this_skillname = stringcleaner(this_skillname) if this_skillname is not None else None
                        skillname.append(this_skillname)
                        skillscore.append(score.attrib["value"])
                except:
                    pass

            entry = pd.DataFrame({
                "simname": [simname],
                "id": [id],
                "x": [x_loc],
                "y": [y_loc],
                "startingpoint": [startingpoint],
                "choice": [choice],
                "result": [result],
                "sectionid": [sectionid],
                "section": [section],
                "coaching": [coaching],
                "feedback": [feedback],
                "behaviorid": [behaviorid],
                "behavior": [behavior],
                "consequence": [consequence],
                "qtype": [qtype],
                "skillid": [skillid],
                "skillname": [skillname],
                "skillscore": [skillscore],
                "file": [file],
            })
            list_xml.append(entry)

    if len(list_xml) > 0:
        xml = pd.concat(list_xml, ignore_index=True)
        del list_xml

        if len(performancebranch_ids) > 0:
            xml = xml.assign(performancebranch = lambda x: x['startingpoint'].apply(lambda y: 1 if y in performancebranch_ids else 0))
        else:
            xml = xml.assign(performancebranch = 0)

        # Alter dataframe to have 1 row for each skillid
        if split_score:
            lst_col = ['skillid', 'skillname', 'skillscore']

            xml = pd.concat([
                pd.DataFrame(
                    {col: np.repeat(xml[col].values, xml['skillid'].str.len()) for col in xml.columns.drop(lst_col)}
                )\
                .assign(
                    **{lst_col[0]:np.concatenate(xml[lst_col[0]].values)},
                    **{lst_col[1]:np.concatenate(xml[lst_col[1]].values)},
                    **{lst_col[2]:np.concatenate(xml[lst_col[2]].values)}
                ),

                pd.DataFrame(
                    {col: np.repeat(xml[col].values, [0 if x > 0 else 1 for x in xml['skillid'].str.len()] ) for col in xml.columns.drop(lst_col)}
                )
            ], ignore_index=True)[xml.columns]

        return xml
    else:
        return pd.DataFrame()


def sim_levels(df):
    """
    Processes a DataFrame of dialogue logs to determine the hierarchical levels of decisions within a simulation.

    This function analyzes dialogue logs from an ETU simulation, where each dialogue consists of a series of interactions
    represented by `relationid` and `relationtype`. The function computes decision levels, merges paths, identifies performance
    branches, and returns a DataFrame with the decision levels for each dialogue.

    Args:
        df (pandas.DataFrame): A DataFrame containing dialogue logs. It must contain at least the following columns:
            - 'relationid': The unique identifier for each dialogue relationship.
            - 'relationtype': The type of the relationship (used to determine decision points).

    Returns:
        pandas.DataFrame: A DataFrame with columns for 'dialogueid', 'decision_level', 'decision_level_num', and 'performancebranch',
                          representing the hierarchical structure of decisions and their levels in the dialogue tree.
    """
    # Check if data frame contains the required columns
    if not set(['relationid', 'relationtype']).issubset(df.columns):
        print('**ERROR: Data frame does not contain relationid and relationtype')
        return pd.DataFrame()

    ### Step 1: Get unique Dialogue IDs
    levels0 = df\
    .query('not relationid.str.contains("None")')\
    .assign(
        startingpoint = lambda x: x['relationid'].str.split('-', expand=True)[0].astype(int),
        endpoint = lambda x: x['relationid'].str.split('-', expand=True)[1].astype(int)
    )\
    .filter(['startingpoint', 'endpoint'])\
    .drop_duplicates()

    ### Step 2: Find all Dialogue IDs that are Decision Points
    decisions = df\
    .assign(
        startingpoint = lambda x: x['relationid'].str.split('-', expand=True)[0].astype(int),
        endpoint = lambda x: x['relationid'].str.split('-', expand=True)[1].astype(int)
    )\
    .query('relationtype <= 3')\
    .filter(['startingpoint'])\
    .drop_duplicates()\
    ['startingpoint'].to_list()

    ### Step 3: Traverse DOWN, and then back UP the dialogue paths
    levels1 = levels0\
    .rename(columns = {'endpoint': 'goes_to'}, inplace = False)\
    .merge(
        levels0.rename(columns = {'startingpoint': 'comes_from'}, inplace = False),
        how='left',
        left_on = ['goes_to'],
        right_on = ['endpoint']
    )\
    .filter(items=['startingpoint', 'comes_from'])\
    .drop_duplicates()\
    .sort_values(['startingpoint', 'comes_from'])\
    .rename(columns={'startingpoint': 'dialogueid', 'comes_from': 'items'})\
    .query('dialogueid.isin(@decisions) & items.isin(@decisions)', engine='python')

    ### Step 4: Traverse UP, and then back DOWN the dialogue paths
    levels2 = levels0\
    .rename(columns = {'startingpoint': 'comes_from'}, inplace = False)\
    .filter(['endpoint', 'comes_from'])\
    .merge(
        levels0.rename(columns = {'endpoint': 'goes_to'}, inplace = False),
        how='left',
        left_on = ['comes_from'],
        right_on = ['startingpoint']
    )\
    .filter(items=['endpoint', 'goes_to'])\
    .drop_duplicates()\
    .sort_values(['endpoint', 'goes_to'])\
    .rename(columns={'endpoint': 'dialogueid', 'goes_to': 'items'})\
    .query('dialogueid.isin(@decisions) & items.isin(@decisions)', engine='python')

    ### Step 5: Keep results that are common between Steps 3 and 4
    levels3 = levels1\
    .merge(
        levels2,
        how='inner',
        on=['dialogueid', 'items']
    )

    ### Step 6: Combine results from all 3 methods
    if levels1.shape[0] > 0 and levels2.shape[0] > 0:
        levels = levels1\
        .sort_values(['dialogueid', 'items'])\
        .groupby(['dialogueid'])\
        .agg(
            items = ('items', lambda x: ', '.join(x.astype(str)))
        )\
        .reset_index()\
        .merge(
            levels0,
            how='left',
            left_on = ['dialogueid'],
            right_on = ['startingpoint']
        )\
        .drop_duplicates()\
        .sort_values(['dialogueid', 'items', 'endpoint'])\
        .groupby(['dialogueid', 'items'])\
        .agg(
            endpoint = ('endpoint', lambda x: ', '.join(x.astype(str)))
        )\
        .reset_index()\
        .assign(
            method1 = lambda x: x.apply(lambda y: '[' + y['items'] + '] --> [' + y['endpoint'] + ']', axis=1)
        )\
        .filter(['dialogueid', 'method1'])\
        .merge(
            levels2\
            .sort_values(['dialogueid', 'items'])\
            .groupby(['dialogueid'])\
            .agg(
                items = ('items', lambda x: ', '.join(x.astype(str)))
            )\
            .reset_index()\
            .merge(
                levels0,
                how='left',
                left_on = ['dialogueid'],
                right_on = ['startingpoint']
            )\
            .drop_duplicates()\
            .sort_values(['dialogueid', 'items', 'endpoint'])\
            .groupby(['dialogueid', 'items'])\
            .agg(
                endpoint = ('endpoint', lambda x: ', '.join(x.astype(str)))
            )\
            .reset_index()\
            .assign(
                method2 = lambda x: x.apply(lambda y: '[' + y['items'] + '] --> [' + y['endpoint'] + ']', axis=1)
            )\
            .filter(['dialogueid', 'method2']),
            how='outer',
            on=['dialogueid']
        )\
        .assign(
            method2 = lambda x: x.apply(lambda y: y['method1'] if pd.isnull(y['method2']) or ('-->' not in y['method2'] and '-->' in y['method1']) else y['method2'], axis=1)
        )\
        .merge(
            levels3\
            .sort_values(['dialogueid', 'items'])\
            .groupby(['dialogueid'])\
            .agg(
                items = ('items', lambda x: ', '.join(x.astype(str)))
            )\
            .reset_index()\
            .merge(
                levels0,
                how='left',
                left_on = ['dialogueid'],
                right_on = ['startingpoint']
            )\
            .drop_duplicates()\
            .sort_values(['dialogueid', 'items', 'endpoint'])\
            .groupby(['dialogueid', 'items'])\
            .agg(
                endpoint = ('endpoint', lambda x: ', '.join(x.astype(str)))
            )\
            .reset_index()\
            .assign(
                method3 = lambda x: x.apply(lambda y: '[' + y['items'] + '] --> [' + y['endpoint'] + ']', axis=1)
            )\
            .filter(['dialogueid', 'method3']) ,
            how='outer',
            on=['dialogueid']
        )\
        .assign(
            method1 = lambda x: x.apply(lambda y: y['dialogueid'] if pd.isnull(y['method1']) else y['method1'], axis=1),
            method2 = lambda x: x.apply(lambda y: y['dialogueid'] if pd.isnull(y['method2']) else y['method2'], axis=1),
            decision_level = lambda x: x.apply(lambda y: y['method1'] if pd.isnull(y['method3']) or ('-->' not in y['method3'] and '-->' in y['method1']) else y['method3'], axis=1)
        )

        ### Step 7: Check if any endpoint has multiple different start points and merge the start points together
        def flatten_extend(matrix):
            flat_list = []
            for row in matrix:
                flat_list.extend([int(x) for x in row])
            return sorted(flat_list)

        levels_multi_end = levels.filter(['decision_level']).drop_duplicates()\
        .assign(
            start = lambda x: x['decision_level'].apply(lambda y: y.split('-->')[0].replace('[', '').replace(']', '').replace(' ', '').strip()),
            end = lambda x: x['decision_level'].apply(lambda y: y.split('-->')[1].replace('[', '').replace(']', '').strip()),
            start_list = lambda x: x['start'].apply(lambda y: [x for x in y.split(',')]),
            end_num = lambda x: x.groupby(['end'])['start'].transform('count')
        )

        if any(levels_multi_end['end_num'] > 1):
            list_start_end = []
            for end in levels_multi_end['end'].unique():
                list_start = []
                for i, row in levels_multi_end.query('end == @end').iterrows():
                    list_start.append(row['start_list'])

                list_start_end.append(
                    pd.DataFrame({
                        'end': [end],
                        'decision_level': ['[' + ', '.join([str(x) for x in flatten_extend(list_start)]).strip() + '] --> [' + end + ']'],
                    })
                )

            levels_multi_end_fixed = pd.concat(list_start_end, ignore_index=True)

            levels = levels\
            .assign(
                end = lambda x: x['decision_level'].apply(lambda y: y.split('-->')[1].replace('[', '').replace(']', '').strip()),
            )\
            .drop(columns=['decision_level'])\
            .merge(
                levels_multi_end_fixed,
                how='left',
                on=['end']
            )\
            .drop(columns=['end'])

        ### Step 8: Check for Performance Branches
        if 'performancebranch' in df.columns:
            if df.query('performancebranch == 1').shape[0] > 0:
                levels = levels\
                .merge(
                    df\
                    .query('performancebranch == 1')\
                    .assign(
                        dialogueid = lambda x: x['relationid'].str.split('-', expand=True)[0].astype(int)
                    )\
                    .filter(['dialogueid', 'performancebranch'])\
                    .drop_duplicates(),
                    how='left',
                    on=['dialogueid']
                )
            else:
                levels = levels\
                .assign(
                    performancebranch = 0
                )
        else:
            levels = levels\
            .assign(
                performancebranch = 0
            )

        ### Step 9: Order Sim Levels
        df_levels = levels.copy()

        df_0 = df\
        .query('not relationid.str.contains("None")')\
        .filter(['relationid'])\
        .drop_duplicates()\
        .assign(
            start = lambda x: x['relationid'].apply(lambda y: int(y.split('-')[0])),
            end = lambda x: x['relationid'].apply(lambda y: int(y.split('-')[1])),
        )

        df_levels_assigned = pd.DataFrame(columns=['decision_level', 'decision_level_num'])

        # Find Sim starting point
        df_next = df_0\
        .merge(
            df_0\
            .filter(['end'])\
            .rename(columns={'end':'start'}),
            how='left',
            on=['start'],
            indicator=True
        )\
        .query('_merge != "both"')\
        .filter(['start'])\
        .drop_duplicates()

        list_levels_assigned = []
        level_num = 0

        list_next = list(dict.fromkeys(df_next['start'].to_list()))
        list_dialogues_used = list_next.copy()
        if len(list_next) > 0 and df_levels.query('dialogueid.isin(@list_next)').shape[0] > 0:
            level_num += 1

            df_levels_assigned = pd.concat([
                df_levels_assigned,
                df_levels.query('dialogueid.isin(@list_next)')\
                    .filter(['decision_level'])\
                    .drop_duplicates()\
                    .assign(
                        decision_level_num = level_num
                    )
            ], ignore_index=True)

            list_levels_assigned = df_levels_assigned['decision_level'].unique()

        loop_num = 0
        while df_levels.shape[0] > 0:
            loop_num+=1

            df_next = df_next\
            .merge(
                df_0,
                how='inner',
                on=['start']
            )\
            .filter(['end'])\
            .drop_duplicates()\
            .rename(columns={'end':'start'})

            list_next = list(dict.fromkeys(df_next['start'].to_list()))
            list_already_used = []
            for e in list_next:
                if e in list_dialogues_used:
                    list_already_used.append(e)

            if len(list_already_used) > 0:
                for e in list_already_used:
                    list_next.remove(e)

            if len(list_next) == 0:
                break

            list_dialogues_used.extend(list_next)
            list_dialogues_used = list(dict.fromkeys(list_dialogues_used))

            if len(list_next) > 0 and df_levels.query('dialogueid.isin(@list_next)').shape[0] > 0:
                level_num += 1

                df_levels_assigned = pd.concat([
                    df_levels_assigned,
                    df_levels.query('dialogueid.isin(@list_next)')\
                        .filter(['decision_level'])\
                        .drop_duplicates()\
                        .assign(
                            decision_level_num = level_num
                        )
                ], ignore_index=True)

                list_levels_assigned = df_levels_assigned['decision_level'].unique()

                df_levels = df_levels\
                .query('not decision_level.isin(@list_levels_assigned)')

        levels = levels\
        .merge(
            df_levels_assigned,
            how='left',
            on=['decision_level']
        )\
        .sort_values(['decision_level_num', 'decision_level', 'dialogueid'])

        # Only return results from first method if all methods are the same
        return(levels.filter(['dialogueid', 'decision_level', 'decision_level_num', 'performancebranch']))

    else:
        return(pd.DataFrame())


def get_decision_levels(pipeline, raw_data, sim_ids, start_dt, end_dt, dict_manual_levels=None,
                       ec2_id=None, ec2_region='us-east-1', s3_bucket_name='etu.appsciences', s3_region='us-east-1'):
    """
    Calculate decision-level performance analytics from XML files and user dialogue logs.

    Implementation:
    1. Fetch XML files from S3 (using EC2 SSM to copy from EC2 instance if needed)
    2. Parse XML files using xml_to_df()
    3. Calculate decision levels using sim_levels()
    4. Join with user_dialogue_log data
    5. Generate decision-level statistics and summaries

    Args:
        pipeline: ParquetPipeline instance
        raw_data: Dictionary of raw DataFrames
        sim_ids: List of simulation IDs
        start_dt: Start date
        end_dt: End date
        dict_manual_levels: Optional manual level overrides
        ec2_id: EC2 instance ID for XML file access (optional)
        ec2_region: EC2 region
        s3_bucket_name: S3 bucket name
        s3_region: S3 region

    Returns:
        pd.DataFrame: Decision levels data with performance metrics

    Source: skillwell_functions.py lines 2751-3415
    """
    logger.info("Calculating Decision Levels...")

    # =========================================================================
    # STEP 1: Get XML File Locations from Simulation Table
    # =========================================================================
    df_sims = raw_data.get('simulation')
    if df_sims is None or df_sims.empty:
        logger.warning("No simulation data found")
        return pd.DataFrame()

    # Filter to requested sims and get XML file URLs
    df_xml_files = df_sims[df_sims['simid'].isin(sim_ids)][['simid', 'name', 'fileUrl']].copy()
    df_xml_files['name'] = df_xml_files['name'].str.strip()

    if df_xml_files.empty:
        logger.warning(f"No XML file URLs found for sims {sim_ids}")
        return pd.DataFrame()

    logger.info(f"Found {len(df_xml_files)} XML files to process")

    # =========================================================================
    # STEP 2: Fetch and Parse XML Files
    # =========================================================================
    list_xml = []

    for i, row in df_xml_files.iterrows():
        simid = row['simid']
        file_url = row['fileUrl']

        logger.info(f"Processing XML for sim {simid}: {file_url}")

        try:
            # --- Copy the XML file from EC2 Instance to S3 Bucket --->
            # (Matching legacy extract_data process from skillwell_functions.py lines 2763-2828)

            ec2_xml_source_file = '/usr/local/etu_sims/' + file_url
            s3_xml_destination_file = 'appsciences/xml/' + '/'.join(file_url.split('/')[1:])

            # Connect to S3
            s3 = boto3.client('s3', region_name=s3_region)

            # Open SSM connection
            ssm_client = boto3.client('ssm', region_name=ec2_region)

            # Copy file from EC2 to S3 via SSM
            response = ssm_client.send_command(
                InstanceIds=[ec2_id],
                DocumentName="AWS-RunShellScript",
                Parameters={'commands': [
                    f'aws s3 cp {ec2_xml_source_file} s3://{s3_bucket_name}/{s3_xml_destination_file}',
                ]}
            )

            time.sleep(2)

            command_id = response['Command']['CommandId']

            output = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=ec2_id,
            )

            waiter = ssm_client.get_waiter('command_executed')
            waiter.wait(
                CommandId=command_id,
                InstanceId=ec2_id,
                PluginName='aws:RunShellScript',
            )

            # --- Read contents of XML File from S3 Bucket --->
            response = s3.get_object(
                Bucket=s3_bucket_name,
                Key=s3_xml_destination_file
            )

            xml_content = response['Body'].read().decode('utf-8')
            logger.info(f"  ✓ Copied from EC2 and read from S3: {s3_xml_destination_file}")

            # Delete XML file from S3 Bucket (cleanup)
            session = boto3.Session(region_name=s3_region)
            s3_session = session.resource('s3')

            s3_session.Object(
                s3_bucket_name,
                'appsciences/xml/' + '/'.join(file_url.split('/')[1:])
            ).delete()
            logger.info(f"  ✓ {file_url} copied and deleted from S3 Bucket successfully.")

            # Parse XML to DataFrame
            this_xml_as_df = xml_to_df(xml_content, split_score=True)

            if isinstance(this_xml_as_df, pd.DataFrame) and not this_xml_as_df.empty:
                # Add relationid, relationtype, decisiontype
                this_xml_as_df = this_xml_as_df.assign(
                    relationid=lambda x: x.apply(lambda y: str(y['startingpoint']) + '-' + str(y['id']), axis=1),
                    relationtype=lambda x: x['qtype'].apply(
                        lambda y: 1 if y == 'critical' else 2 if y == 'suboptimal' else 3 if y == 'optimal' else 4
                    ),
                    decisiontype=lambda x: x['qtype'].apply(
                        lambda y: y.capitalize() if pd.notnull(y) else None
                    ),
                    simid=simid
                )

                list_xml.append(this_xml_as_df)
                logger.info(f"  ✓ Parsed XML: {len(this_xml_as_df)} elements")

        except Exception as e:
            logger.error(f"  ❌ Error processing XML for sim {simid}: {e}")
            continue

    if not list_xml:
        logger.warning("No XML files successfully parsed")
        return pd.DataFrame()

    # Combine all XML data
    df_xml = pd.concat(list_xml, ignore_index=True)
    logger.info(f"Total XML elements parsed: {len(df_xml)}")

    # =========================================================================
    # STEP 3: Calculate Decision Levels using sim_levels()
    # =========================================================================
    list_sim_levels = []

    for simid in df_xml['simid'].unique():
        logger.info(f"Calculating decision levels for sim {simid}...")

        df_this_sim = df_xml.query('simid == @simid and not relationid.str.contains("None")', engine='python')

        if df_this_sim.empty:
            continue

        # Get decision levels
        df_this_sim_levels = sim_levels(
            df_this_sim[['relationid', 'relationtype', 'performancebranch']].drop_duplicates()
        )

        if isinstance(df_this_sim_levels, pd.DataFrame) and not df_this_sim_levels.empty:
            df_this_sim_levels = df_this_sim_levels.assign(simid=simid)

            # Filter to only levels with commas (multiple decisions)
            df_this_sim_levels = df_this_sim_levels.query('decision_level.str.contains(",")', engine='python')

            if not df_this_sim_levels.empty:
                # Add section information
                df_this_sim_levels = df_this_sim_levels.merge(
                    df_xml.assign(
                        dialogueid=lambda x: x['startingpoint'].apply(lambda y: int(y) if pd.notnull(y) else None),
                        sectionid_min=lambda x: x.groupby(['simid', 'sectionid', 'section'])['y'].transform('min')
                    )[['simid', 'dialogueid', 'sectionid', 'section']].drop_duplicates(),
                    how='left',
                    on=['simid', 'dialogueid']
                )\
                .sort_values(['simid', 'decision_level_num', 'decision_level', 'dialogueid', 'sectionid'])\
                .groupby(['simid', 'decision_level_num', 'decision_level', 'dialogueid']).first().reset_index()\
                .sort_values(['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'dialogueid'])

                # Get unique Decision Level Number (based on sort order)
                df_this_sim_levels = df_this_sim_levels.drop(columns=['decision_level_num']).merge(
                    df_this_sim_levels[['simid', 'sectionid', 'section', 'decision_level']]\
                    .drop_duplicates()\
                    .assign(decision_level_num=lambda x: x.groupby(['simid'])['decision_level'].cumcount() + 1),
                    how='left',
                    on=['simid', 'sectionid', 'section', 'decision_level']
                )

                # Add scenario text
                df_this_sim_levels = df_this_sim_levels.merge(
                    df_xml.assign(
                        dialogueid=lambda x: x['relationid'].apply(lambda y: int(y.split('-')[1]) if pd.notnull(y) else None),
                        decision_type=lambda x: x['qtype'].apply(
                            lambda y: 1 if y == 'optimal' else 2 if y == 'suboptimal' else 3 if y == 'critical' else 4
                        )
                    )[['simid', 'dialogueid', 'result', 'decision_type']]\
                    .drop_duplicates()\
                    .rename(columns={'result': 'scenario'})\
                    .merge(
                        df_this_sim_levels[['simid', 'dialogueid', 'decision_level_num', 'decision_level']],
                        how='inner',
                        on=['simid', 'dialogueid']
                    )\
                    .sort_values(['simid', 'decision_level_num', 'decision_level', 'decision_type', 'dialogueid'])\
                    .groupby(['simid', 'decision_level_num', 'decision_level']).first().reset_index()\
                    [['simid', 'decision_level_num', 'decision_level', 'scenario']].drop_duplicates(),
                    how='left',
                    on=['simid', 'decision_level_num', 'decision_level']
                ).assign(
                    scenario=lambda x: x.apply(
                        lambda y: 'Decision Level #' + str(int(y['decision_level_num'])) if pd.isnull(y['scenario']) else y['scenario'],
                        axis=1
                    )
                )

                # Handle duplicate scenarios across levels
                df_this_sim_levels = df_this_sim_levels.drop(columns=['scenario']).merge(
                    df_this_sim_levels[['simid', 'scenario', 'decision_level_num', 'decision_level']]\
                    .drop_duplicates()\
                    .assign(
                        scenario_dec_num=lambda x: x.groupby(['simid', 'scenario'])['decision_level'].cumcount(),
                        scenario=lambda x: x.apply(
                            lambda y: y['scenario'] + ' ' * int(y['scenario_dec_num']) if pd.notnull(y['scenario_dec_num']) else y['scenario'],
                            axis=1
                        )
                    ).drop(columns=['scenario_dec_num']),
                    how='left',
                    on=['simid', 'decision_level_num', 'decision_level']
                )

                list_sim_levels.append(df_this_sim_levels)
                logger.info(f"  ✓ Calculated {len(df_this_sim_levels)} decision levels")

    if not list_sim_levels:
        logger.warning("No decision levels calculated")
        return pd.DataFrame()

    df_sim_levels = pd.concat(list_sim_levels, ignore_index=True)

    # =========================================================================
    # STEP 4: Create Model Levels with Choice/Feedback/Coaching
    # =========================================================================
    df_sim_model_levels = df_sim_levels.merge(
        df_xml.query('relationid.notnull() and not relationid.str.contains("None")', engine='python')\
        [['simid', 'relationid', 'decisiontype', 'choice', 'feedback', 'coaching']].drop_duplicates()\
        .assign(dialogueid=lambda x: x['relationid'].apply(lambda y: int(y.split('-')[0]))),
        how='left',
        on=['simid', 'dialogueid']
    )

    # Add choice_num
    df_sim_model_levels = df_sim_model_levels.merge(
        df_sim_model_levels[['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decisiontype', 'choice']]\
        .drop_duplicates()\
        .assign(choice_num=lambda x: x.groupby(['simid', 'sectionid', 'decision_level', 'decisiontype'])['choice'].cumcount() + 1),
        how='left',
        on=['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decisiontype', 'choice']
    )

    # =========================================================================
    # STEP 5: Apply Manual Level Overrides (if provided)
    # =========================================================================
    if dict_manual_levels is not None:
        logger.info("Applying manual decision level overrides...")
        for key_manual, val_manual in dict_manual_levels.items():
            list_simid_manual = list(key_manual) if isinstance(key_manual, tuple) else [key_manual]

            for simid_manual in list_simid_manual:
                for key_level, val_level in val_manual.items():
                    df_sim_levels = df_sim_levels.assign(
                        decision_level=lambda x: x.apply(
                            lambda y: val_level if y['simid'] == simid_manual and y['decision_level'] in key_level else y['decision_level'],
                            axis=1
                        )
                    )

                    df_sim_model_levels = df_sim_model_levels.assign(
                        decision_level=lambda x: x.apply(
                            lambda y: val_level if y['simid'] == simid_manual and y['decision_level'] in key_level else y['decision_level'],
                            axis=1
                        )
                    )

    logger.info("Decision levels calculated successfully")

    # =========================================================================
    # STEP 6: Join with User Dialogue Logs and Calculate Statistics
    # =========================================================================
    logger.info("Calculating user statistics for decision levels...")

    # Get filtered logs and valid users
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    if df_logs_filtered.empty:
        logger.warning("No valid user logs found")
        return pd.DataFrame()

    # Get dialogue logs
    df_dialogues = raw_data.get('user_dialogue_log')
    if df_dialogues is None or df_dialogues.empty:
        logger.warning("No dialogue logs found")
        return pd.DataFrame()

    # Filter dialogues for valid users
    df_dialogues_filtered = df_dialogues[
        df_dialogues['userid'].isin(valid_uids) &
        df_dialogues['simid'].isin(sim_ids) &
        df_dialogues['relationid'].notnull()
    ].copy()

    # Map relationType -> relationtype
    df_dialogues_filtered['relationtype'] = df_dialogues_filtered['relationType']

    # Create decision_level_num mapping from sim_model_levels
    decision_level_mapping = df_sim_model_levels[['simid', 'decision_level_num', 'relationid']].drop_duplicates()

    # Join dialogues with decision levels
    df_dialogues_with_levels = df_dialogues_filtered.merge(
        decision_level_mapping,
        on=['simid', 'relationid'],
        how='inner'
    )

    # Mark first and last attempts
    df_logs_with_attempts = df_logs_filtered.copy()
    df_logs_with_attempts['first_attempt'] = df_logs_with_attempts.groupby(['simid', 'userid'])['start'].rank(method='first')
    df_logs_with_attempts['last_attempt'] = df_logs_with_attempts.groupby(['simid', 'userid'])['start'].rank(method='first', ascending=False)

    df_logs_first_last = df_logs_with_attempts[
        (df_logs_with_attempts['first_attempt'] == 1) |
        ((df_logs_with_attempts['last_attempt'] == 1) & (df_logs_with_attempts['first_attempt'] != 1))
    ].copy()

    df_logs_first_last['attempt'] = df_logs_first_last['first_attempt'].apply(
        lambda x: 'First Attempt' if x == 1 else 'Last Attempt'
    )

    # Join dialogues with attempts
    df_stats = df_dialogues_with_levels.merge(
        df_logs_first_last[['simid', 'userid', 'logid', 'attempt']],
        on=['simid', 'userid', 'logid'],
        how='inner'
    )

    # Add decision_ord and decisiontype
    df_stats['decision_ord'] = df_stats['relationtype'].map({1: 3, 2: 2, 3: 1})
    df_stats['decisiontype'] = df_stats['relationtype'].map({1: 'Critical', 2: 'Suboptimal', 3: 'Optimal'})

    # Calculate stats - actual counts from user data
    df_actual_stats = df_stats.groupby([
        'simid', 'attempt', 'decision_level_num', 'decision_ord', 'decisiontype'
    ]).agg({'userid': 'nunique'}).reset_index().rename(columns={'userid': 'n'})

    # Get simulation names
    df_sims_names = df_sims[['simid', 'name']].rename(columns={'name': 'simname'})
    df_sims_names['simname'] = df_sims_names['simname'].str.strip()

    # =========================================================================
    # FILL IN ZEROS: Create all combinations of (decision_level, decisiontype, attempt)
    # Legacy SQL does a RIGHT JOIN to ensure all combinations exist even if n=0
    # =========================================================================

    # Get all unique decision level metadata from sim_model_levels
    merge_cols = ['simid', 'sectionid', 'section', 'decision_level', 'decision_level_num', 'scenario', 'decisiontype', 'choice', 'choice_num', 'decision_ord']
    if 'feedback' in df_sim_model_levels.columns:
        merge_cols.append('feedback')
    if 'coaching' in df_sim_model_levels.columns:
        merge_cols.append('coaching')

    # Add decision_ord to sim_model_levels if not present
    if 'decision_ord' not in df_sim_model_levels.columns:
        df_sim_model_levels['decision_ord'] = df_sim_model_levels['decisiontype'].map({
            'Optimal': 1, 'Suboptimal': 2, 'Critical': 3
        })

    df_all_levels = df_sim_model_levels[merge_cols].drop_duplicates()

    # Get all attempts (First Attempt, Last Attempt)
    df_all_attempts = df_stats[['simid', 'attempt']].drop_duplicates()

    # Cross join: all decision levels × all attempts
    df_all_combos = df_all_levels.merge(df_all_attempts, on='simid', how='left')

    # LEFT JOIN with actual stats to get n values
    df_summary = df_all_combos.merge(
        df_actual_stats[['simid', 'attempt', 'decision_level_num', 'decisiontype', 'n']],
        on=['simid', 'attempt', 'decision_level_num', 'decisiontype'],
        how='left'
    )

    # Fill missing n values with 0
    df_summary['n'] = df_summary['n'].fillna(0).astype(int)

    # Add simname
    df_summary = df_summary.merge(df_sims_names, on='simid', how='left')

    # Calculate total_decision per (simid, attempt, decision_level_num)
    df_summary['total_decision'] = df_summary.groupby(['simid', 'attempt', 'decision_level_num'])['n'].transform('sum')

    # Calculate percentages
    df_summary['pct'] = df_summary.apply(
        lambda x: (x['n'] / x['total_decision'] * 100) if x['total_decision'] > 0 else 0, axis=1
    )

    # Assign to df_final
    df_final = df_summary

    # Add colors
    df_final['bar_color'] = df_final['decisiontype'].map({
        'Optimal': '#339933',
        'Suboptimal': '#ffb833',
        'Critical': '#e32726'
    })

    # Add missing metadata columns
    # total_attempt: total users for this attempt type per sim
    total_attempt_df = df_stats.groupby(['simid', 'attempt']).agg({'userid': 'nunique'}).reset_index().rename(columns={'userid': 'total_attempt'})
    df_final = df_final.merge(total_attempt_df, on=['simid', 'attempt'], how='left')

    # total_sim: total users per sim (same as total_attempt for first attempt typically)
    total_sim_df = df_stats.groupby(['simid']).agg({'userid': 'nunique'}).reset_index().rename(columns={'userid': 'total_sim'})
    df_final = df_final.merge(total_sim_df, on=['simid'], how='left')

    # attempt_n: formatted string like "First Attempt\n(2,626 Learners)"
    df_final['attempt_n'] = df_final.apply(
        lambda x: f"{x['attempt']}\n({x['total_attempt']:,} Learners)" if pd.notnull(x['total_attempt']) else x['attempt'],
        axis=1
    )

    # rect_height: always 1.0 for bar chart rendering
    df_final['rect_height'] = 1.0

    # skills: list of skills associated with each decision level (from XML)
    # Get skills from xml data if available
    if 'df_xml' in dir() and df_xml is not None and 'scoreid' in df_xml.columns:
        # Would need to join skills here - for now use placeholder
        df_final['skills'] = None
    else:
        df_final['skills'] = None

    # Ensure feedback and coaching columns exist and convert NULL to "-" (matching SQL behavior)
    # SQL: feedback = lambda x: x['feedback'].apply(lambda y: "-" if pd.isnull(y) else y)
    if 'feedback' not in df_final.columns:
        df_final['feedback'] = '-'
    else:
        df_final['feedback'] = df_final['feedback'].apply(lambda y: "-" if pd.isnull(y) else y)

    if 'coaching' not in df_final.columns:
        df_final['coaching'] = '-'
    else:
        df_final['coaching'] = df_final['coaching'].apply(lambda y: "-" if pd.isnull(y) else y)

    # Sort final output
    df_final = df_final.sort_values([
        'simid', 'attempt', 'sectionid', 'decision_level_num', 'decision_level', 'decision_ord', 'decisiontype', 'choice_num', 'choice'
    ])

    # Convert data types to match original SQL output (which uses float64 for nullable integers)
    # Original SQL returns float64 for choice_num, decision_level_num, decision_ord due to NULL handling
    df_final['choice_num'] = df_final['choice_num'].astype('float64')
    df_final['decision_level_num'] = df_final['decision_level_num'].astype('float64')
    df_final['decision_ord'] = df_final['decision_ord'].astype('float64')

    logger.info(f"✓ Decision levels complete: {len(df_final)} rows")

    # Also return df_sim_model_levels for use in dmg_decision_levels
    # It contains the relationid -> decision_level_num mapping needed for demographic breakdown
    return df_final, df_sim_model_levels


# =============================================================================
# PROJECT-LEVEL AGGREGATIONS
# =============================================================================

def get_proj_engagement(df_learner_engagement, df_sims, dict_project, dict_sim_order, raw_data=None, start_date=None, end_date=None):
    """
    Calculate project-level engagement metrics.
    Aggregates learner engagement across multiple sims in a project.

    Source: skillwell_functions.py lines 4803-4907
    """
    logger.info("Calculating Project Engagement...")

    if df_learner_engagement is None or df_learner_engagement.empty:
        return pd.DataFrame()

    if dict_project is None:
        return pd.DataFrame()

    # Create project mapping from dict_project {(sim1, sim2): 'Project Name'}
    dict_project_alt = {}
    project_sim_counts = {}  # Count of sims per project
    for sims, project_name in dict_project.items():
        project_sim_counts[project_name] = len(sims)
        for sim in sims:
            dict_project_alt[sim] = project_name

    # Add project column to learner engagement
    df_eng = df_learner_engagement.copy()
    df_eng['project'] = df_eng['simid'].map(dict_project_alt)

    # Calculate total users per project (users who completed at least one sim)
    # stat_order == 2 is "Completed"
    df_completed = df_eng[df_eng['stat_order'] == 2].copy()

    if df_completed.empty:
        return pd.DataFrame()

    # Calculate users who completed ALL sims in project
    # Need raw user_sim_log data to count completions per user
    total_all_complete = 0
    if raw_data is not None:
        df_logs = raw_data.get('user_sim_log')
        df_users = raw_data.get('user')
        if df_logs is not None and not df_logs.empty:
            # Handle bytes vs int for complete column
            if df_logs['complete'].dtype == object:
                complete_mask = df_logs['complete'] == b'\x01'
            else:
                complete_mask = df_logs['complete'] == 1

            # Get completed logs
            df_log_complete = df_logs[complete_mask].copy()
            df_log_complete['project'] = df_log_complete['simid'].map(dict_project_alt)

            # Filter to role=1 users only
            if df_users is not None and not df_users.empty:
                role1_users = df_users[df_users['roleid'] == 1]['userid'].unique()
                df_log_complete = df_log_complete[df_log_complete['userid'].isin(role1_users)]

            # Count distinct sims completed per user per project
            user_sim_counts = df_log_complete.groupby(['project', 'userid'])['simid'].nunique().reset_index()
            user_sim_counts.rename(columns={'simid': 'sims_completed'}, inplace=True)

            # Count users who completed all sims
            for project_name, sim_count in project_sim_counts.items():
                users_all_complete = user_sim_counts[
                    (user_sim_counts['project'] == project_name) &
                    (user_sim_counts['sims_completed'] >= sim_count)
                ]['userid'].nunique()
                total_all_complete = users_all_complete

    # Calculate project-level total (unique users who completed ANY sim in the project)
    # This matches legacy SQL: COUNT(DISTINCT userid) FROM stats_tbl GROUP BY project
    # Must apply same date filtering as filter_logs_and_users (first_start_dt >= start_date)
    total_users = 0
    if raw_data is not None:
        df_logs = raw_data.get('user_sim_log')
        df_users = raw_data.get('user')
        if df_logs is not None and not df_logs.empty:
            # Handle bytes vs int for complete column
            if df_logs['complete'].dtype == object:
                complete_mask = df_logs['complete'] == b'\x01'
            else:
                complete_mask = df_logs['complete'] == 1

            # Get all completed logs for project sims
            all_project_sims = list(dict_project_alt.keys())
            df_log_complete = df_logs[complete_mask & df_logs['simid'].isin(all_project_sims)].copy()

            # Filter to role=1 users only
            if df_users is not None and not df_users.empty:
                role1_users = df_users[df_users['roleid'] == 1]['userid'].unique()
                df_log_complete = df_log_complete[df_log_complete['userid'].isin(role1_users)]

            # Apply date filtering to match filter_logs_and_users logic
            # Calculate first_start_dt per user/sim and filter where first_start_dt >= start_date
            if start_date is not None and end_date is not None:
                df_log_complete['start'] = pd.to_datetime(df_log_complete['start'])
                df_log_complete['end'] = pd.to_datetime(df_log_complete['end'])
                df_log_complete['start_date_only'] = df_log_complete['start'].dt.floor('d')
                df_log_complete['first_start_dt'] = df_log_complete.groupby(['simid', 'userid'])['start_date_only'].transform('min')

                target_start = pd.to_datetime(start_date).floor('d')
                target_end = pd.to_datetime(end_date).floor('d')

                # Filter: user's first attempt must be >= start_date, and end <= end_date
                df_log_complete = df_log_complete[
                    (df_log_complete['first_start_dt'] >= target_start) &
                    (df_log_complete['end'].dt.floor('d') <= target_end)
                ]

            # Total unique users who completed any sim in project
            total_users = df_log_complete['userid'].nunique()

    # Use project-level total for all rows
    df_proj = df_completed.copy()
    df_proj['total'] = total_users
    df_proj['pct'] = (df_proj['n'] / df_proj['total'] * 100) if total_users > 0 else 0

    # Add all_complete metrics
    df_proj['total_all_complete'] = total_all_complete
    df_proj['pct_all_complete'] = (total_all_complete / total_users * 100) if total_users > 0 else 0

    # Add sim_order
    df_proj['sim_order'] = df_proj['simid'].map(dict_sim_order)
    df_proj = df_proj.sort_values('sim_order')

    logger.info(f"✓ Project engagement complete: {len(df_proj)} rows")
    return df_proj


def get_proj_time_spent(df_time_spent, dict_project, dict_sim_order):
    """
    Calculate project-level time spent metrics.

    Source: skillwell_functions.py lines 5077-5084
    """
    logger.info("Calculating Project Time Spent...")

    if df_time_spent is None or df_time_spent.empty:
        return pd.DataFrame()

    if dict_project is None:
        return pd.DataFrame()

    # Filter to stat_order == 1 (primary stat)
    df_proj = df_time_spent.query('stat_order == 1').copy()

    if df_proj.empty:
        return pd.DataFrame()

    # Add project and sort order
    dict_project_alt = {}
    for sims, project_name in dict_project.items():
        for sim in sims:
            dict_project_alt[sim] = project_name

    df_proj['project'] = df_proj['simid'].map(dict_project_alt)
    df_proj['sim_order'] = df_proj['simid'].map(dict_sim_order)
    df_proj = df_proj.sort_values('sim_order')

    logger.info(f"✓ Project time spent complete: {len(df_proj)} rows")
    return df_proj


def get_proj_practice_mode(df_practice_mode, dict_project, dict_sim_order):
    """
    Calculate project-level practice mode metrics.

    Source: skillwell_functions.py lines 5089-5095
    """
    logger.info("Calculating Project Practice Mode...")

    if df_practice_mode is None or df_practice_mode.empty:
        return pd.DataFrame()

    if dict_project is None:
        return pd.DataFrame()

    df_proj = df_practice_mode.copy()

    # Add project and sort order
    dict_project_alt = {}
    for sims, project_name in dict_project.items():
        for sim in sims:
            dict_project_alt[sim] = project_name

    df_proj['project'] = df_proj['simid'].map(dict_project_alt)
    df_proj['sim_order'] = df_proj['simid'].map(dict_sim_order)
    df_proj = df_proj.sort_values('sim_order')

    logger.info(f"✓ Project practice mode complete: {len(df_proj)} rows")
    return df_proj


# =============================================================================
# DEMOGRAPHIC AGGREGATIONS
# =============================================================================

def get_dmg_vars(df_demog):
    """
    Extract unique demographic variable/value pairs.

    Source: skillwell_functions.py lines 5111-5117
    """
    logger.info("Calculating Demographic Variables...")

    if df_demog is None or df_demog.empty:
        return pd.DataFrame()

    list_demog_var_vals = []

    # Get all demographic columns (exclude uid, userid, languageid, and ordering columns)
    demog_cols = [x for x in df_demog.columns if x not in ['uid', 'userid', 'languageid'] and '_ord' not in x]

    for demog_var in demog_cols:
        sort_ord = demog_var + '_ord' if (demog_var + '_ord') in df_demog.columns else demog_var

        # Get unique values, sorted by ordering column if available
        if sort_ord in df_demog.columns:
            unique_vals = df_demog.sort_values(sort_ord)[demog_var].unique()
        else:
            unique_vals = df_demog[demog_var].unique()

        for demog_val in unique_vals:
            list_demog_var_vals.append(pd.DataFrame({
                'demog_var': [demog_var],
                'demog_val': [demog_val]
            }))

    if not list_demog_var_vals:
        return pd.DataFrame()

    df_dmg_vars = pd.concat(list_demog_var_vals, ignore_index=True)
    logger.info(f"✓ Demographic variables complete: {len(df_dmg_vars)} rows")
    return df_dmg_vars


def get_dmg_engagement(raw_data, df_demog, sim_ids, start_dt, end_dt, dict_project=None):
    """
    Calculate learner engagement broken down by demographics.

    Source: skillwell_functions.py lines 5124-5220
    """
    logger.info("Calculating Demographic Engagement...")

    if df_demog is None or df_demog.empty:
        return pd.DataFrame()

    df_logs = raw_data.get('user_sim_log')
    df_users = raw_data.get('user')
    df_sims = raw_data.get('simulation')

    if df_logs is None or df_logs.empty:
        return pd.DataFrame()

    # Filter logs by sim and date
    df_logs = df_logs[df_logs['simid'].isin(sim_ids)].copy()

    # Convert BIT columns to integers
    def convert_bit(x):
        if isinstance(x, bytes): return int.from_bytes(x, "big")
        try: return int(x)
        except: return 0

    for col in ['complete', 'pass', 'assess']:
        if col in df_logs.columns:
            df_logs[col] = df_logs[col].apply(convert_bit)

    # Ensure date columns
    if 'start' in df_logs.columns:
        df_logs['start'] = pd.to_datetime(df_logs['start'])
    if 'end' in df_logs.columns:
        df_logs['end'] = pd.to_datetime(df_logs['end'])

    # Calculate first attempt date per user/sim
    df_logs['start_dt'] = df_logs.groupby(['simid', 'userid'])['start'].transform('min')

    # Filter by date range
    df_logs = df_logs[df_logs['start_dt'] >= start_dt]
    df_logs = df_logs[df_logs['end'] <= end_dt]

    # Filter to role=1 users
    if df_users is not None and not df_users.empty:
        role1_users = df_users[df_users['roleid'] == 1][['userid', 'uid']]
        df_logs = df_logs.merge(role1_users, on='userid', how='inner')
    else:
        return pd.DataFrame()

    # Calculate completion status per user/sim
    user_stats = df_logs.groupby(['simid', 'userid', 'uid']).agg({
        'complete': 'sum'
    }).reset_index()

    # Assign stat (completed or not)
    user_stats['stat_order'] = user_stats['complete'].apply(lambda x: 2 if x >= 1 else 1)
    user_stats['stat'] = user_stats['stat_order'].apply(lambda x: 'Completed' if x == 2 else 'Not Completed')
    user_stats['bar_color'] = user_stats['stat_order'].apply(lambda x: '#4285f4' if x == 2 else '#d3d2d2')

    # Add simname
    if df_sims is not None and not df_sims.empty:
        df_sims_clean = df_sims[['simid', 'name']].copy()
        df_sims_clean['name'] = df_sims_clean['name'].str.strip()
        df_sims_clean.rename(columns={'name': 'simname'}, inplace=True)
        user_stats = user_stats.merge(df_sims_clean, on='simid', how='left')

    # Merge with demographics
    user_stats = user_stats.merge(df_demog, on='uid', how='inner', suffixes=('', '_demog'))

    # Get demographic columns (exclude uid, userid, languageid, and ordering columns)
    demog_cols = [x for x in df_demog.columns if x not in ['uid', 'userid', 'languageid'] and '_ord' not in x]

    # Group by sim, stat, and each demographic column
    group_cols = ['simid', 'simname', 'stat_order', 'stat', 'bar_color'] + demog_cols

    df_dmg_eng = user_stats.groupby(group_cols).agg(
        _n=('uid', 'nunique')
    ).reset_index()

    df_dmg_eng = df_dmg_eng.sort_values(['simid', 'stat_order'])

    # Add project if provided
    if dict_project is not None:
        dict_project_alt = {}
        for sims, project_name in dict_project.items():
            for sim in sims:
                dict_project_alt[sim] = project_name
        df_dmg_eng['project'] = df_dmg_eng['simid'].map(dict_project_alt)

    logger.info(f"✓ Demographic engagement complete: {len(df_dmg_eng)} rows")
    return df_dmg_eng


def get_dmg_skill_baseline(raw_data, df_demog, sim_ids, start_dt, end_dt, dict_project=None):
    """
    Calculate skill baseline broken down by demographics.

    Source: skillwell_functions.py lines 5222-5338
    """
    logger.info("Calculating Demographic Skill Baseline...")

    if df_demog is None or df_demog.empty:
        return pd.DataFrame()

    df_logs = raw_data.get('user_sim_log')
    df_users = raw_data.get('user')
    df_scores = raw_data.get('score')
    df_sim_scores = raw_data.get('sim_score_log')
    df_sims = raw_data.get('simulation')

    if df_logs is None or df_sim_scores is None or df_scores is None:
        return pd.DataFrame()

    # Filter logs to relevant sims
    df_logs = df_logs[df_logs['simid'].isin(sim_ids)].copy()

    # Ensure date columns
    if 'start' in df_logs.columns:
        df_logs['start'] = pd.to_datetime(df_logs['start'])

    # Calculate first attempt date
    df_logs['start_dt'] = df_logs.groupby(['simid', 'userid'])['start'].transform('min')
    df_logs = df_logs[df_logs['start_dt'] >= start_dt]

    # Filter to first attempts only
    df_logs.sort_values(['userid', 'simid', 'start'], inplace=True)
    df_logs['attempt'] = df_logs.groupby(['userid', 'simid']).cumcount() + 1
    df_first = df_logs[df_logs['attempt'] == 1].copy()

    # Filter to role=1 users and get uid
    if df_users is not None and not df_users.empty:
        role1_users = df_users[df_users['roleid'] == 1][['userid', 'uid']]
        df_first = df_first.merge(role1_users, on='userid', how='inner')
    else:
        return pd.DataFrame()

    # Join with scores (sim_score_log has 'value' column, rename to 'pct' for consistency)
    df_sim_scores_sel = df_sim_scores[['logid', 'scoreid', 'value']].rename(columns={'value': 'pct'})
    df_first = df_first.merge(df_sim_scores_sel, on='logid', how='inner')
    # Score table has 'label' not 'name', include orderid
    score_name_col = 'label' if 'label' in df_scores.columns else 'name'
    score_cols = ['scoreid', score_name_col, 'hidden']
    if 'orderid' in df_scores.columns:
        score_cols.append('orderid')
    df_first = df_first.merge(df_scores[score_cols], on='scoreid', how='inner')
    df_first.rename(columns={score_name_col: 'skillname'}, inplace=True)

    # Add simname
    if df_sims is not None and not df_sims.empty:
        df_sims_clean = df_sims[['simid', 'name']].copy()
        df_sims_clean['name'] = df_sims_clean['name'].str.strip()
        df_sims_clean.rename(columns={'name': 'simname'}, inplace=True)
        df_first = df_first.merge(df_sims_clean, on='simid', how='left')

    # Merge with demographics
    df_first = df_first.merge(df_demog, on='uid', how='inner', suffixes=('', '_demog'))

    # Get demographic columns (exclude uid, userid, languageid, and ordering columns)
    demog_cols = [x for x in df_demog.columns if x not in ['uid', 'userid', 'languageid'] and '_ord' not in x]

    # Group by sim, skill, and demographics to get total scores (matching reference format)
    # SQL uses: _n = ('skillscore', 'count'), _tot = ('skillscore', 'sum')
    # This means _n is COUNT of all rows (not unique users), _tot is SUM of scores
    group_cols = ['simid', 'simname', 'skillname'] + demog_cols
    if 'orderid' in df_first.columns:
        group_cols.insert(2, 'orderid')

    df_dmg_skill = df_first.groupby(group_cols).agg(
        _n=('pct', 'count'),   # COUNT of all rows (skillscores), not unique users
        _tot=('pct', 'sum')    # SUM of scores
    ).reset_index()

    # Add attempt column (always "First Attempt" since we filter to first attempts)
    df_dmg_skill['attempt'] = 'First Attempt'

    # Add project if provided
    if dict_project is not None:
        dict_project_alt = {}
        for sims, project_name in dict_project.items():
            for sim in sims:
                dict_project_alt[sim] = project_name
        df_dmg_skill['project'] = df_dmg_skill['simid'].map(dict_project_alt)

    logger.info(f"✓ Demographic skill baseline complete: {len(df_dmg_skill)} rows")
    return df_dmg_skill


def get_dmg_decision_levels(df_decision_levels, df_demog, raw_data, sim_ids, dict_project=None, df_sim_model_levels=None):
    """
    Calculate decision levels broken down by demographics.

    This replicates skillwell_functions.py lines 5340-5555:
    - Uses relationid -> decision_level_num mapping from df_sim_model_levels
    - Groups by ALL demographic columns at once (creating cross-product)
    - Includes both first and last attempts
    - Merges with decision level info from XML
    - Calculates _n (count) and _denom (denominator for percentage)

    Source: skillwell_functions.py lines 5340-5555
    """
    logger.info("Calculating Demographic Decision Levels...")

    if df_decision_levels is None or df_decision_levels.empty:
        logger.warning("No decision_levels data available")
        return pd.DataFrame()

    if df_demog is None or df_demog.empty:
        logger.warning("No demographic data available")
        return pd.DataFrame()

    df_users = raw_data.get('user')
    df_dialogue_log = raw_data.get('user_dialogue_log')
    df_logs = raw_data.get('user_sim_log')
    df_sims = raw_data.get('simulation')

    if df_users is None or df_dialogue_log is None or df_logs is None:
        logger.warning("Missing required raw data tables")
        return pd.DataFrame()

    # Get role=1 users with uid
    role1_users = df_users[df_users['roleid'] == 1][['userid', 'uid']].copy()

    # Get demographic columns (excluding uid, userid, languageid, and _ord columns)
    demog_cols = [x for x in df_demog.columns if x not in ['uid', 'userid', 'languageid'] and '_ord' not in x]

    if not demog_cols:
        logger.warning("No demographic columns found")
        return pd.DataFrame()

    # Create project mapping
    dict_project_alt = {}
    dict_sim_order = {}
    if dict_project is not None:
        for i, (sims, project_name) in enumerate(dict_project.items()):
            for j, sim in enumerate(sims):
                dict_project_alt[sim] = project_name
                dict_sim_order[sim] = j

    # =========================================================================
    # Step 1: Build user attempt data (first and last attempts)
    # Replicates SQL subquery t2_1 from skillwell_functions.py
    # =========================================================================

    # Filter completed logs for relevant sims
    df_logs_sim = df_logs[df_logs['simid'].isin(sim_ids)].copy()

    # Handle complete column (may be bytes or int)
    if df_logs_sim['complete'].dtype == object:
        complete_mask = df_logs_sim['complete'].apply(
            lambda x: int.from_bytes(x, "big") if isinstance(x, bytes) else int(x) if pd.notnull(x) else 0
        ) == 1
    else:
        complete_mask = df_logs_sim['complete'] == 1

    df_logs_complete = df_logs_sim[complete_mask].copy()

    # Calculate first and last attempt ranks
    df_logs_complete['first_attempt'] = df_logs_complete.groupby(['simid', 'userid'])['start'].rank(method='first')
    df_logs_complete['last_attempt'] = df_logs_complete.groupby(['simid', 'userid'])['start'].rank(method='first', ascending=False)

    # Create attempt labels (First Attempt and Last Attempt where different from first)
    first_attempts = df_logs_complete[df_logs_complete['first_attempt'] == 1].copy()
    first_attempts['attempt'] = 'First Attempt'

    last_attempts = df_logs_complete[
        (df_logs_complete['last_attempt'] == 1) &
        (df_logs_complete['first_attempt'] != 1)
    ].copy()
    last_attempts['attempt'] = 'Last Attempt'

    df_attempts = pd.concat([first_attempts, last_attempts], ignore_index=True)

    # =========================================================================
    # Step 2: Get dialogue log data with decision info
    # Replicates SQL subquery t2_4 from skillwell_functions.py
    # The key is mapping relationid -> decision_level_num using df_sim_model_levels
    # =========================================================================

    # Filter dialogue log to relevant sims with relationid (decisions)
    df_dialogue = df_dialogue_log[
        df_dialogue_log['simid'].isin(sim_ids) &
        df_dialogue_log['relationid'].notnull() &
        (df_dialogue_log['relationType'] <= 3)
    ].copy()

    # Map relationtype to decisiontype and decision_ord
    df_dialogue['decisiontype'] = df_dialogue['relationType'].map({1: 'Critical', 2: 'Suboptimal', 3: 'Optimal'})
    df_dialogue['decision_ord'] = df_dialogue['relationType'].map({1: 3, 2: 2, 3: 1})

    # Map relationid -> decision_level_num using df_sim_model_levels (if provided)
    # This is the critical step that gives us the proper decision level breakdown
    if df_sim_model_levels is not None and 'relationid' in df_sim_model_levels.columns:
        # Get the mapping from sim_model_levels
        decision_level_mapping = df_sim_model_levels[['simid', 'decision_level_num', 'relationid', 'choice_num']].drop_duplicates()
        df_dialogue = df_dialogue.merge(
            decision_level_mapping,
            on=['simid', 'relationid'],
            how='inner'
        )
    else:
        # Fallback: cannot determine decision_level_num per user without relationid mapping
        logger.warning("df_sim_model_levels not provided - cannot map relationid to decision_level_num")
        # Use a simplified approach - get all unique decision levels and join based on decisiontype
        # This won't give per-user-per-level breakdown but at least maintains demographics
        pass

    # =========================================================================
    # Step 3: Join attempts with dialogue log and users
    # =========================================================================

    # Build columns to select from df_dialogue
    dialogue_cols = ['simid', 'userid', 'logid', 'decisiontype', 'decision_ord', 'end']
    if 'decision_level_num' in df_dialogue.columns:
        dialogue_cols.append('decision_level_num')
    if 'choice_num' in df_dialogue.columns:
        dialogue_cols.append('choice_num')

    # Join dialogue with attempts (logid is the key link)
    df_merged = df_attempts.merge(
        df_dialogue[dialogue_cols],
        on=['simid', 'userid', 'logid'],
        how='inner'
    )

    # Add uid from users
    df_merged = df_merged.merge(role1_users, on='userid', how='inner')

    # Join with demographics (this creates the cross-product naturally)
    df_merged = df_merged.merge(df_demog, on='uid', how='inner', suffixes=('', '_demog'))

    # Get simname
    if df_sims is not None:
        df_merged = df_merged.merge(
            df_sims[['simid', 'name']].rename(columns={'name': 'simname'}),
            on='simid',
            how='left'
        )

    # =========================================================================
    # Step 4: Get decision level info from df_decision_levels (XML-derived)
    # =========================================================================

    # Get unique decision level metadata
    decision_cols = ['simid', 'decision_level_num', 'decision_level', 'sectionid', 'section',
                     'scenario', 'decisiontype', 'choice', 'choice_num', 'decision_ord', 'bar_color']
    if 'feedback' in df_decision_levels.columns:
        decision_cols.extend(['feedback', 'coaching'])

    df_decision_info = df_decision_levels[decision_cols].drop_duplicates()

    # =========================================================================
    # Step 5: Aggregate by demographics, decision level, and decision type
    # This is the key groupby that creates the cross-product of all demographic columns
    # Replicates: .groupby(['simid', 'simname', 'attempt', 'decision_level_num', 'decision_ord',
    #                       'decisiontype', 'choice_num'] + demog_cols)
    # =========================================================================

    # Group by all demographic columns at once (creates cross-product)
    # Include decision_level_num if we have it from relationid mapping
    if 'decision_level_num' in df_merged.columns:
        groupby_cols = ['simid', 'simname', 'attempt', 'decision_level_num', 'decision_ord', 'decisiontype', 'choice_num'] + demog_cols
    else:
        groupby_cols = ['simid', 'simname', 'attempt', 'decision_ord', 'decisiontype'] + demog_cols

    df_grouped = df_merged.groupby(groupby_cols).agg(
        _n=('userid', 'count')
    ).reset_index()

    # =========================================================================
    # Step 6: Merge with decision level info from XML
    # =========================================================================

    # Get sim_levels info for decision_level_num mapping
    df_sim_levels = df_decision_levels[['simid', 'sectionid', 'section', 'decision_level',
                                         'decision_level_num', 'scenario']].drop_duplicates()

    # Merge to get section/scenario info
    if 'decision_level_num' in df_grouped.columns:
        df_grouped = df_grouped.merge(
            df_sim_levels,
            on=['simid', 'decision_level_num'],
            how='left'
        )
    else:
        # If no decision_level_num, use decisiontype to get info
        df_dec_unique = df_decision_info.drop_duplicates(subset=['simid', 'decisiontype'])
        df_grouped = df_grouped.merge(
            df_dec_unique[['simid', 'decisiontype', 'decision_level_num', 'choice_num']],
            on=['simid', 'decisiontype'],
            how='left'
        )
        df_grouped = df_grouped.merge(
            df_sim_levels,
            on=['simid', 'decision_level_num'],
            how='left'
        )

    # =========================================================================
    # Step 7: Merge with choice text
    # =========================================================================

    df_model_levels = df_decision_levels[['simid', 'sectionid', 'section', 'decision_level',
                                           'decisiontype', 'choice_num', 'choice']].drop_duplicates()

    df_grouped = df_grouped.merge(
        df_model_levels,
        on=['simid', 'sectionid', 'section', 'decision_level', 'decisiontype', 'choice_num'],
        how='left'
    )

    # =========================================================================
    # Step 8: Fill in zeros and calculate _denom
    # Replicates the zero-fill merge and _denom calculation
    # =========================================================================

    # Get all unique combinations that should exist
    combo_cols = demog_cols + ['simid', 'simname', 'sectionid', 'section',
                                'decision_level_num', 'decision_level', 'scenario',
                                'decision_ord', 'decisiontype', 'choice_num', 'choice']
    # Filter to only include columns that exist in df_grouped
    combo_cols = [c for c in combo_cols if c in df_grouped.columns]
    all_combos = df_grouped[combo_cols].drop_duplicates()

    # Cross with attempts
    attempts_df = pd.DataFrame({'attempt': ['First Attempt', 'Last Attempt']})
    all_combos = all_combos.merge(attempts_df, how='cross')

    # Right merge to fill in zeros
    merge_cols = [c for c in combo_cols if c in all_combos.columns] + ['attempt']
    df_grouped = df_grouped.merge(
        all_combos,
        on=merge_cols,
        how='right'
    )

    # Fill NaN _n with 0
    df_grouped['_n'] = df_grouped['_n'].fillna(0).astype(int)

    # Calculate _denom (total users per demographic group per decision level)
    denom_group_cols = demog_cols + ['simid', 'simname', 'attempt', 'sectionid', 'section',
                                      'decision_level_num', 'decision_level', 'scenario']
    denom_group_cols = [c for c in denom_group_cols if c in df_grouped.columns]
    df_grouped['_denom'] = df_grouped.groupby(denom_group_cols)['_n'].transform('sum')

    # Adjust _denom to only show on first row of each group (matching original behavior)
    df_grouped['_meh'] = df_grouped.groupby(denom_group_cols)['_n'].cumcount() + 1
    df_grouped['_denom'] = df_grouped.apply(lambda y: y['_denom'] if y['_meh'] == 1 else 0, axis=1)
    df_grouped.drop(columns=['_meh'], inplace=True)

    # =========================================================================
    # Step 9: Add bar_color, sim_order, decision_level_basic
    # =========================================================================

    df_grouped['bar_color'] = df_grouped['decisiontype'].apply(
        lambda y: '#339933' if y == 'Optimal' else '#ffb833' if y == 'Suboptimal' else '#e32726'
    )
    df_grouped['sim_order'] = df_grouped['simid'].map(dict_sim_order)
    if 'decision_level_num' in df_grouped.columns:
        df_grouped['decision_level_basic'] = df_grouped['decision_level_num'].apply(
            lambda y: 'Decision Level ' + str(int(y)) if pd.notnull(y) else None
        )
    else:
        df_grouped['decision_level_basic'] = None

    # =========================================================================
    # Step 10: Merge feedback and coaching
    # =========================================================================

    if 'feedback' in df_decision_levels.columns and 'sectionid' in df_grouped.columns:
        fb_cols = df_decision_levels[['simid', 'sectionid', 'decision_level_num', 'decision_level',
                                       'decisiontype', 'choice_num', 'feedback', 'coaching']].drop_duplicates()
        fb_cols = fb_cols.groupby(['simid', 'sectionid', 'decision_level_num', 'decision_level',
                                    'decisiontype', 'choice_num']).first().reset_index()

        df_grouped = df_grouped.merge(
            fb_cols,
            on=['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num'],
            how='left'
        )
        df_grouped['feedback'] = df_grouped['feedback'].fillna('-')
        df_grouped['coaching'] = df_grouped['coaching'].fillna('-')
    else:
        df_grouped['feedback'] = '-'
        df_grouped['coaching'] = '-'

    # =========================================================================
    # Step 11: Add project and sort
    # =========================================================================

    if dict_project is not None:
        df_grouped['project'] = df_grouped['simid'].map(dict_project_alt)

    # Sort to match original order
    sort_cols = ['sim_order', 'attempt', 'sectionid', 'decision_level_num', 'decision_level',
                 'decision_ord', 'decisiontype', 'choice_num', 'choice']
    sort_cols = [c for c in sort_cols if c in df_grouped.columns]
    df_grouped = df_grouped.sort_values(sort_cols)

    # Convert data types to match original SQL output (float64 for nullable integers)
    if 'choice_num' in df_grouped.columns:
        df_grouped['choice_num'] = df_grouped['choice_num'].astype('float64')
    if 'decision_level_num' in df_grouped.columns:
        df_grouped['decision_level_num'] = df_grouped['decision_level_num'].astype('float64')
    if 'decision_ord' in df_grouped.columns:
        df_grouped['decision_ord'] = df_grouped['decision_ord'].astype('float64')

    logger.info(f"✓ Demographic decision levels complete: {len(df_grouped)} rows")
    return df_grouped


def get_base_demographics_from_parquet(pipeline, sim_ids):
    """
    Extract base demographic data (uid, Language) from Parquet files.
    Equivalent to the SQL query for 'First Completed Attempt'.
    """
    logger.info("Extracting base demographics from Parquet...")
    
    # 1. Load Raw Data needed
    raw_data = pipeline.load_raw_data_for_analysis(sim_ids=sim_ids)
    df_logs = raw_data.get('user_sim_log')
    if df_logs is None or df_logs.empty:
        return pd.DataFrame()

    # 2. Filter Completed & Relevant Sims
    # Handle bytes vs int comparison for 'complete' column (Parquet stores as bytes)
    if df_logs['complete'].dtype == object:
        # Bytes comparison (b'\x01' for True)
        complete_mask = df_logs['complete'] == b'\x01'
    else:
        # Integer comparison
        complete_mask = df_logs['complete'] == 1

    df_logs_complete = df_logs[
        complete_mask &
        (df_logs['simid'].isin(sim_ids))
    ].copy()
    
    if df_logs_complete.empty:
        return pd.DataFrame()

    # Ensure dates
    if 'end' in df_logs_complete.columns:
        df_logs_complete['end'] = pd.to_datetime(df_logs_complete['end'])
    
    # 3. Sort by 'end' date (Ascending, so first end date is top)
    df_logs_complete.sort_values(by=['simid', 'userid', 'end'], ascending=[True, True, True], inplace=True)
    
    # 4. Drop duplicates to keep first attempt per sim/user
    df_first_attempts = df_logs_complete.drop_duplicates(subset=['simid', 'userid'], keep='first')
    
    # 5. Join Language
    df_language = raw_data.get('language')
    if df_language is not None and not df_language.empty:
        lang_col = 'languageid' if 'languageid' in df_first_attempts.columns else 'languageId'
        if lang_col in df_first_attempts.columns:
            df_merged = df_first_attempts.merge(
                df_language[['id', 'name']], 
                left_on=lang_col, 
                right_on='id', 
                how='left'
            ).rename(columns={'name': 'Language', 'id': 'Language_ord'})
        else:
            df_merged = df_first_attempts.copy()
            df_merged['Language'] = None
            df_merged['Language_ord'] = None
    else:
        df_merged = df_first_attempts.copy()
        df_merged['Language'] = None
        df_merged['Language_ord'] = None
    
    # 6. Join User (Role ID = 1)
    df_user = raw_data.get('user')
    if df_user is not None and not df_user.empty:
        df_user_role1 = df_user[df_user['roleid'] == 1].copy()
        df_demog = df_merged.merge(
            df_user_role1[['userid', 'uid']],
            on='userid',
            how='inner'
        )
        if 'uid_y' in df_demog.columns:
             df_demog.rename(columns={'uid_y': 'uid'}, inplace=True)
    else:
        df_demog = df_merged.copy()
        df_demog['uid'] = None

    # Final Selection
    if 'uid' in df_demog.columns:
        # Ensure extraction includes Language columns if present
        cols = ['uid']
        if 'Language' in df_demog.columns: cols.append('Language')
        if 'Language_ord' in df_demog.columns: cols.append('Language_ord')
        return df_demog[cols].copy()
    
    return pd.DataFrame()

def get_transformed_data_from_parquet(pipeline, sim_ids, start_date, end_date, df_demog=None,
                                       dict_project=None,
                                       ec2_id=None, ec2_region='us-east-1',
                                       s3_bucket_name='etu.appsciences', s3_region='us-east-1'):
    """
    Load raw data from Parquet and transform it into the format expected by the report.

    Args:
        pipeline: ParquetPipeline instance
        sim_ids: list of sim IDs
        start_date: str YYYY-MM-DD
        end_date: str YYYY-MM-DD
        df_demog (pd.DataFrame, optional): Pre-merged demographic dataframe (Client + System data)
        dict_project (dict, optional): Dictionary linking sim IDs to project names.
            Format: {(sim1, sim2): 'Project Name'} or {sim1: 'Project Name'}
        ec2_id (str, optional): EC2 instance ID for XML file access via SSM
        ec2_region (str, optional): AWS region for EC2 instance (default: 'us-east-1')
        s3_bucket_name (str, optional): S3 bucket name for XML files (default: 'etu.appsciences')
        s3_region (str, optional): AWS region for S3 bucket (default: 'us-east-1')
    """
    logger.info(f"Transforming data for sims: {sim_ids}")
    
    # 1. Load Raw Data
    # NOTE: Do NOT pass date filters here - let filter_logs_and_users handle date filtering
    # to match original SQL behavior (which calculates first_start_dt before filtering)
    raw_data = pipeline.load_raw_data_for_analysis(
        sim_ids=sim_ids
    )
    
    df_logs = raw_data.get('user_sim_log')
    df_sims = raw_data.get('simulation')
    
    if df_logs is None or df_logs.empty:
        logger.warning("No user_sim_log data found.")
        return {}
        
    # [Rest of casting and date logic...]
    if 'start' in df_logs.columns:
        df_logs['start'] = pd.to_datetime(df_logs['start'])
    if 'end' in df_logs.columns:
        df_logs['end'] = pd.to_datetime(df_logs['end'])

    # Ensure BIT columns are integers
    for col in ['complete', 'pass', 'assess']:
        if col in df_logs.columns:
            def convert_bit(x):
                if isinstance(x, bytes): return int.from_bytes(x, "big")
                try: return int(x)
                except: return 0
            df_logs[col] = df_logs[col].apply(convert_bit)
        
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # -------------------------------------------------------------------------
    # OPTIONAL: Filter logs by demographics (if df_demog provided)
    # -------------------------------------------------------------------------
    if df_demog is not None and not df_demog.empty:
        # Placeholder for rigorous uid mapping if needed
        pass

    # -------------------------------------------------------------------------
    # FILTER 0: Apply Strict User & Date Filtering (Global)
    # -------------------------------------------------------------------------
    # This creates the "valid population" for most downstream stats.
    # Note: df_logs_filtered contains only Role=1, First Attempt >= Start Date, etc.
    df_logs_filtered, valid_uids = filter_logs_and_users(raw_data, sim_ids, start_dt, end_dt)

    # -------------------------------------------------------------------------
    # TRANSFORMATION 1: Learner Engagement
    # -------------------------------------------------------------------------
    df_learner_engagement = get_learner_engagement(df_logs_filtered, df_sims)

    # -------------------------------------------------------------------------
    # TRANSFORMATION 2: Engagement Over Time
    # -------------------------------------------------------------------------
    # ... [Re-using existing logic logic (lines 107-166)] ...
    period_days = (end_dt - start_dt).days + 1
    
    # Split frequency alias: Period vs Offset
    # to_period requires 'M', 'Q'
    freq_period = 'D' if period_days <= 30 else 'W' if period_days <= 112 else 'M' if period_days <= 730 else 'Q'
    # Grouper/Offset prefers 'ME', 'QE' in new Pandas
    freq_offset = 'D' if period_days <= 30 else 'W' if period_days <= 112 else 'ME' if period_days <= 730 else 'QE'
    
    df_completed = df_logs[df_logs['complete'] == 1].copy()
    df_completed['dt'] = df_completed['end'].dt.to_period(freq_period).dt.to_timestamp() 
    
    if not df_completed.empty:
        gw = df_completed.groupby(['simid', pd.Grouper(key='end', freq=freq_offset)])
        df_time = gw.size().reset_index(name='n')
        df_time['dt'] = df_time['end']
        df_time['n_cum'] = df_time.groupby('simid')['n'].cumsum()

        df_totals = df_time.groupby('simid')['n'].sum().reset_index(name='total')
        
        df_time = df_time.merge(df_totals, on='simid')
        df_time['pct'] = (df_time['n'] / df_time['total']) * 100
        
        engagement_time_results = df_time
        
        if not engagement_time_results.empty and not df_sims.empty:
             engagement_time_results = engagement_time_results.merge(df_sims[['simid', 'name']], on='simid', how='left')
             engagement_time_results.rename(columns={'name': 'simname'}, inplace=True)
             
    else:
        engagement_time_results = pd.DataFrame()

    # -------------------------------------------------------------------------
    # TRANSFORMATION 3: Overall Pass Rates
    # -------------------------------------------------------------------------
    # ... [Re-using existing logic (lines 169-248)] ...
    df_logs.sort_values(['userid', 'simid', 'start'], inplace=True)
    df_logs['attempt_calc'] = df_logs.groupby(['userid', 'simid']).cumcount() + 1
    if 'pass' not in df_logs.columns: df_logs['pass'] = 0 
    
    pass_results = []
    
    for simid, group in df_logs.groupby('simid'):
        user_status = []
        for userid, user_logs in group.groupby('userid'):
            passed_logs = user_logs[user_logs['pass'] == 1]
            if not passed_logs.empty:
                first_pass = passed_logs.iloc[0]
                status = f"Passed Attempt {min(first_pass['attempt_calc'], 4)}" 
                if first_pass['attempt_calc'] >= 4:
                    status = "Passed Attempt 4+"
                else:
                    status = f"Passed Attempt {first_pass['attempt_calc']}"
            else:
                completed_logs = user_logs[user_logs['complete'] == 1]
                status = "Completed, not yet Passed" if not completed_logs.empty else "Incomplete"
            
            if status != "Incomplete": user_status.append(status)
                
        from collections import Counter
        counts = Counter(user_status)
        total = sum(counts.values())
        rows = [
            {'simid': simid, 'stat_order': 1, 'stat': 'Passed Attempt 1', 'n': counts.get('Passed Attempt 1', 0), 'total': total},
            {'simid': simid, 'stat_order': 2, 'stat': 'Passed Attempt 2', 'n': counts.get('Passed Attempt 2', 0), 'total': total},
            {'simid': simid, 'stat_order': 3, 'stat': 'Passed Attempt 3', 'n': counts.get('Passed Attempt 3', 0), 'total': total},
            {'simid': simid, 'stat_order': 4, 'stat': 'Passed Attempt 4+', 'n': counts.get('Passed Attempt 4+', 0), 'total': total},
            {'simid': simid, 'stat_order': 5, 'stat': 'Completed, not yet Passed', 'n': counts.get('Completed, not yet Passed', 0), 'total': total}
        ]
        pass_results.extend(rows)
    df_pass_rates = pd.DataFrame(pass_results)
    if not df_pass_rates.empty and not df_sims.empty:
        df_pass_rates = df_pass_rates.merge(df_sims[['simid', 'name']], on='simid', how='left')
        df_pass_rates.rename(columns={'name': 'simname'}, inplace=True)
        df_pass_rates['pct'] = (df_pass_rates['n'] / df_pass_rates['total']) * 100

    # -------------------------------------------------------------------------
    # TRANSFORMATION 4: Demographic Data
    # -------------------------------------------------------------------------
    # If df_demog was passed in (from Excel merge), use it.
    # Otherwise, calculate base demographics from Parquet if needed, or leave empty.
    # The logic we extracted to get_base_demographics_from_parquet covers the Parquet part.
    if df_demog is None:
        # Fallback: calculate base if not provided
        # Or better: use the helper we just defined!
        df_demog_final = get_base_demographics_from_parquet(pipeline, sim_ids)
    else:
        df_demog_final = df_demog

    # -------------------------------------------------------------------------
    # TRANSFORMATION 5: Skill Baseline & Survey Responses
    # -------------------------------------------------------------------------
    df_skill_baseline = get_skill_baseline(pipeline, raw_data, sim_ids, start_dt, end_dt)
    df_survey_responses = get_survey_responses(pipeline, raw_data, sim_ids, start_dt, end_dt)

    # -------------------------------------------------------------------------
    # TRANSFORMATION 6: Additional Sim-Level Metrics (NEWLY IMPLEMENTED)
    # -------------------------------------------------------------------------
    logger.info("Calculating additional sim-level metrics...")
    df_skill_improvement = get_skill_improvement(pipeline, raw_data, sim_ids, start_dt, end_dt, show_hidden_skills=True)
    df_time_spent = get_time_spent(pipeline, raw_data, sim_ids, start_dt, end_dt)
    df_practice_mode = get_practice_mode(pipeline, raw_data, sim_ids, start_dt, end_dt)
    df_learner_engagement_over_time = get_learner_engagement_over_time(pipeline, raw_data, sim_ids, start_dt, end_dt)

    # Decision levels (full implementation with EC2 SSM support)
    # Returns tuple: (df_decision_levels, df_sim_model_levels)
    # df_sim_model_levels contains relationid -> decision_level_num mapping for dmg_decision_levels
    df_decision_levels, df_sim_model_levels = get_decision_levels(
        pipeline, raw_data, sim_ids, start_dt, end_dt,
        ec2_id=ec2_id, ec2_region=ec2_region,
        s3_bucket_name=s3_bucket_name, s3_region=s3_region
    )

    # -------------------------------------------------------------------------
    # TRANSFORMATION 7: Setup Project Mapping and Sim Ordering
    # -------------------------------------------------------------------------
    logger.info("Setting up project mapping...")

    # Use passed dict_project or default
    if dict_project is None:
        dict_project = {tuple(sim_ids): 'Our Code: We Respect One Another'}

    # Create project lookup: simid -> project name
    dict_project_alt = {}
    for k, v in dict_project.items():
        if isinstance(k, int):
            dict_project_alt[k] = v
        else:
            for simid in k:
                dict_project_alt[simid] = v

    # Create sim ordering
    dict_sim_order = {simid: i for i, simid in enumerate(sim_ids)}

    # -------------------------------------------------------------------------
    # TRANSFORMATION 8: Add project and sim_order to all DataFrames
    # -------------------------------------------------------------------------
    logger.info("Adding project and sim_order columns...")

    def add_project_sim_order(df):
        """Add project and sim_order columns to DataFrame if simid exists."""
        if df is None or df.empty:
            return df
        if 'simid' in df.columns:
            df = df.copy()
            df['project'] = df['simid'].map(dict_project_alt)
            # Use float64 for sim_order to match original SQL output (handles NaN properly)
            df['sim_order'] = df['simid'].map(dict_sim_order).astype('float64')
        return df

    # Add to sim-level DataFrames
    df_learner_engagement = add_project_sim_order(df_learner_engagement)
    # Remove sim_order from learner_engagement to match original schema
    if df_learner_engagement is not None and 'sim_order' in df_learner_engagement.columns:
        df_learner_engagement = df_learner_engagement.drop(columns=['sim_order'])
    df_learner_engagement_over_time = add_project_sim_order(df_learner_engagement_over_time)
    # Remove sim_order from learner_engagement_over_time to match original schema
    if df_learner_engagement_over_time is not None and 'sim_order' in df_learner_engagement_over_time.columns:
        df_learner_engagement_over_time = df_learner_engagement_over_time.drop(columns=['sim_order'])
    df_pass_rates = add_project_sim_order(df_pass_rates)
    df_skill_baseline = add_project_sim_order(df_skill_baseline)
    # Remove sim_order from skill_baseline to match original schema
    if df_skill_baseline is not None and 'sim_order' in df_skill_baseline.columns:
        df_skill_baseline = df_skill_baseline.drop(columns=['sim_order'])
    df_skill_improvement = add_project_sim_order(df_skill_improvement)
    # Remove sim_order from skill_improvement to match original schema
    if df_skill_improvement is not None and 'sim_order' in df_skill_improvement.columns:
        df_skill_improvement = df_skill_improvement.drop(columns=['sim_order'])
    df_decision_levels = add_project_sim_order(df_decision_levels)
    # Convert sim_order to int64 for decision_levels to match original SQL output
    if df_decision_levels is not None and 'sim_order' in df_decision_levels.columns:
        df_decision_levels['sim_order'] = df_decision_levels['sim_order'].astype('int64')
    df_time_spent = add_project_sim_order(df_time_spent)
    # Remove sim_order from time_spent to match original schema
    if df_time_spent is not None and 'sim_order' in df_time_spent.columns:
        df_time_spent = df_time_spent.drop(columns=['sim_order'])
    df_practice_mode = add_project_sim_order(df_practice_mode)
    # Remove sim_order from practice_mode and reorder columns to match original schema
    if df_practice_mode is not None and 'sim_order' in df_practice_mode.columns:
        df_practice_mode = df_practice_mode.drop(columns=['sim_order'])
    # Reorder columns to match original: simid, simname, total, n, pct, avg_practice_duration, project
    if df_practice_mode is not None and not df_practice_mode.empty:
        expected_cols = ['simid', 'simname', 'total', 'n', 'pct', 'avg_practice_duration', 'project']
        available_cols = [c for c in expected_cols if c in df_practice_mode.columns]
        df_practice_mode = df_practice_mode[available_cols]
    df_survey_responses = add_project_sim_order(df_survey_responses)

    # Add dt_char to engagement_over_time
    # Format depends on time_freq: 'd' -> "Jan 01, 2025", 'w' -> "Jan 01, 2025", 'm' -> "Aug 2025", 'q' -> "Q1 2025", 'y' -> "2025"
    if df_learner_engagement_over_time is not None and not df_learner_engagement_over_time.empty:
        if 'dt' in df_learner_engagement_over_time.columns and 'time_freq' in df_learner_engagement_over_time.columns:
            time_freq = df_learner_engagement_over_time['time_freq'].iloc[0] if len(df_learner_engagement_over_time) > 0 else 'm'
            # Convert dt from string to datetime for formatting, then keep dt as string
            dt_datetime = pd.to_datetime(df_learner_engagement_over_time['dt'])
            if time_freq == 'd':
                df_learner_engagement_over_time['dt_char'] = dt_datetime.dt.strftime('%b %d, %Y')
            elif time_freq == 'w':
                df_learner_engagement_over_time['dt_char'] = dt_datetime.dt.strftime('%b %d, %Y')
            elif time_freq == 'm':
                df_learner_engagement_over_time['dt_char'] = dt_datetime.dt.strftime('%b %Y')
            elif time_freq == 'q':
                df_learner_engagement_over_time['dt_char'] = dt_datetime.apply(
                    lambda x: f"Q{(x.month - 1) // 3 + 1} {x.year}"
                )
            else:  # 'y'
                df_learner_engagement_over_time['dt_char'] = dt_datetime.dt.strftime('%Y')

    # Add opac to time_spent
    if df_time_spent is not None and not df_time_spent.empty:
        df_time_spent['opac'] = 1.0

    # -------------------------------------------------------------------------
    # TRANSFORMATION 9: Project-Level Aggregations
    # -------------------------------------------------------------------------
    logger.info("Calculating project-level aggregations...")

    df_proj_engagement = get_proj_engagement(df_learner_engagement, df_sims, dict_project, dict_sim_order, raw_data=raw_data, start_date=start_dt, end_date=end_dt)
    df_proj_time_spent = get_proj_time_spent(df_time_spent, dict_project, dict_sim_order)
    df_proj_practice_mode = get_proj_practice_mode(df_practice_mode, dict_project, dict_sim_order)

    # Add project columns to engagement_over_time for proj level
    engagement_time_results = add_project_sim_order(engagement_time_results)
    if engagement_time_results is not None and not engagement_time_results.empty:
        if 'dt' in engagement_time_results.columns:
            engagement_time_results['dt_char'] = engagement_time_results['dt'].dt.strftime('%Y-%m-%d') if hasattr(engagement_time_results['dt'].iloc[0], 'strftime') else engagement_time_results['dt'].astype(str)
        # Add missing columns for proj_engagement_over_time
        engagement_time_results['bar_color'] = '#4285f4'
        engagement_time_results['time_freq'] = 'm'  # monthly
        # complete_any_sim = total users who completed at least one sim in project
        if 'total' in engagement_time_results.columns:
            engagement_time_results['complete_any_sim'] = engagement_time_results['total']
        else:
            engagement_time_results['complete_any_sim'] = 0

    # -------------------------------------------------------------------------
    # TRANSFORMATION 10: Demographic Aggregations
    # -------------------------------------------------------------------------
    logger.info("Calculating demographic aggregations...")

    df_dmg_vars = get_dmg_vars(df_demog_final)
    df_dmg_engagement = get_dmg_engagement(raw_data, df_demog_final, sim_ids, start_dt, end_dt, dict_project)
    df_dmg_skill_baseline = get_dmg_skill_baseline(raw_data, df_demog_final, sim_ids, start_dt, end_dt, dict_project)
    df_dmg_decision_levels = get_dmg_decision_levels(df_decision_levels, df_demog_final, raw_data, sim_ids, dict_project, df_sim_model_levels)

    # -------------------------------------------------------------------------
    # TRANSFORMATION 11: Final Cleanup - Create proj_sims and sims
    # -------------------------------------------------------------------------
    # Create simplified sims DataFrame matching reference format
    df_sims_simple = pd.DataFrame({
        'sim_order': [dict_sim_order.get(sid, i) for i, sid in enumerate(sim_ids)],
        'simid': sim_ids,
        'simname': [df_sims[df_sims['simid'] == sid]['name'].values[0].strip() if not df_sims[df_sims['simid'] == sid].empty else f'Sim {sid}' for sid in sim_ids],
        'project': [dict_project_alt.get(sid, '') for sid in sim_ids]
    })

    # -------------------------------------------------------------------------
    # Return Dictionary (Matching dict_df.json structure)
    # -------------------------------------------------------------------------
    logger.info("Transformation complete. Formatting as dict_df...")

    # NOTE: Key order matters! The report() function iterates over dict_df keys
    # in order to build menus/tabs. Original SQL extract_data returns:
    # ['proj', 'sim', 'srv', 'dmg'] - we must match this order.
    dict_df = {
        'proj': {
            'proj_sims': df_sims_simple,
            'proj_engagement': df_proj_engagement,
            'proj_engagement_over_time': engagement_time_results,
            'proj_time_spent': df_proj_time_spent,
            'proj_practice_mode': df_proj_practice_mode,
            'proj_nps': pd.DataFrame(),  # Calculated in reporting.py
        },
        # NOTE: sim sub-key order matches original extract_data output.
        # overall_pass_rates is excluded to match original (extract_data has overall_pass_rates=False)
        'sim': {
             'sims': df_sims_simple,
             'learner_engagement': df_learner_engagement,
             'learner_engagement_over_time': df_learner_engagement_over_time,
             'skill_baseline': df_skill_baseline,
             'skill_improvement': df_skill_improvement,
             'decision_levels': df_decision_levels,
             'time_spent': df_time_spent,
             'practice_mode': df_practice_mode,
        },
        'srv': {
            'survey_responses': df_survey_responses
        },
        # NOTE: dmg sub-key order matters! The report() function uses index-based
        # logic (i_key2 == 1 triggers 'var data_component_dmg = {').
        # Original order: dmg_vars, dmg_engagement, dmg_skill_baseline, dmg_decision_levels
        # Do NOT include demographic_data - it breaks the report() function.
        'dmg': {
            'dmg_vars': df_dmg_vars,
            'dmg_engagement': df_dmg_engagement,
            'dmg_skill_baseline': df_dmg_skill_baseline,
            'dmg_decision_levels': df_dmg_decision_levels,
        },
    }

    return dict_df
