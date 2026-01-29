
import os
import sys
from datetime import time, date, datetime, timezone, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import pickle


# Add parent directory to path to allow importing sibling modules
if __name__ == '__main__' and __package__ is None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir_poc = os.path.dirname(current_dir)
    sys.path.append(parent_dir_poc)
    from skillwell_etl.pipeline import ParquetPipeline
    from skillwell_etl.transform import get_transformed_data_from_parquet, get_base_demographics_from_parquet
else:
    from .pipeline import ParquetPipeline
    from .transform import get_transformed_data_from_parquet, get_base_demographics_from_parquet

# Add 'Our Code' directory to path to import skillwell_functions
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
skillwell_dir = os.path.join(parent_dir, "Our Code We Respect One Another")
if skillwell_dir not in sys.path:
    sys.path.append(skillwell_dir)


# Import report function and find_ec2 from legacy script
try:
    from skillwell_functions import report, find_ec2
except ImportError:
    logging.warning("Could not import 'report' or 'find_ec2' from skillwell_functions.py. Report generation might fail.")
    def report(*args, **kwargs): return "<html><body>Report generation failed (missing function)</body></html>"
    def find_ec2(customer): return (None, 'us-east-1')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GenerateReport')

# -----------------------------------------------------------------------------
# Modular Plotting Functions
# -----------------------------------------------------------------------------

def plot_learner_engagement(df):
    """Generates Bar chart for Learner Engagement (Attempts)."""
    if df is None or df.empty:
        return None
        
    fig = go.Figure()
    for simid, group in df.groupby('simid'):
        simname = group['simname'].iloc[0] if 'simname' in group.columns else f"Sim {simid}"
        fig.add_trace(go.Bar(
            x=group['stat'], y=group['n'],
            name=f"{simname} - Engagement",
            marker_color='#1f77b4'
        ))
    fig.update_layout(title="Learner Engagement (Attempts)", yaxis_title="Users")
    return fig

def plot_pass_rates(df):
    """Generates Bar chart for Overall Pass Rates."""
    if df is None or df.empty:
        return None

    fig = go.Figure()
    for simid, group in df.groupby('simid'):
        simname = group['simname'].iloc[0] if 'simname' in group.columns else f"Sim {simid}"
        fig.add_trace(go.Bar(
            x=group['stat'], y=group['pct'],
            name=f"{simname} - Pass Rate (%)",
            text=group['pct'].apply(lambda x: f"{x:.1f}%"),
            textposition='auto',
            marker_color='#2ca02c'
        ))
    fig.update_layout(title="Overall Pass Rates", yaxis_title="Percentage (%)", yaxis_range=[0, 100])
    return fig

def plot_engagement_over_time(df):
    """Generates Line chart for Engagement Over Time."""
    if df is None or df.empty:
        return None
        
    fig = go.Figure()
    # Normalize 'dt' column if present to ensure proper plotting
    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'])
        
    for simid, group in df.groupby('simid'):
        simname = group['simname'].iloc[0] if 'simname' in group.columns else f"Sim {simid}"
        group = group.sort_values('dt')
        fig.add_trace(go.Scatter(
            x=group['dt'], y=group['n'],
            mode='lines+markers',
            name=f"{simname} - Daily/Weekly Users",
            line=dict(width=2)
        ))
    fig.update_layout(title="Learner Engagement Over Time", yaxis_title="Users")
    return fig

def plot_nps_scores(df):
    """Generates Horizontal Bar chart for NPS Scores."""
    if df is None or df.empty:
        return None
        
    # Aggregate data for plotting (one bar per sim usually)
    # Assuming df has 'avg_nps_score' per sim
    agg_df = df.groupby(['simname'])['avg_nps_score'].mean().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=agg_df['simname'],
        x=agg_df['avg_nps_score'],
        orientation='h',
        marker=dict(
            color=agg_df['avg_nps_score'],
            colorscale='RdYlGn',
            cmin=-1, cmax=1
        ),
        text=agg_df['avg_nps_score'].apply(lambda x: f"{x:.2f}"),
        textposition='auto'
    ))
    fig.update_layout(title="Net Promoter Score (NPS)", xaxis_range=[-1, 1], xaxis_title="Score")
    return fig

def plot_skill_polar_chart(df):
    """Generates Polar/Radar chart for Skill Baseline."""
    if df is None or df.empty:
        return None

    fig = go.Figure()
    
    # Filter for relevant skills (exclude overall usually, or handle separately)
    # For now, plot all
    for simid, group in df.groupby('simid'):
        simname = group['simname'].iloc[0] if 'simname' in group.columns else f"Sim {simid}"
        
        # Ensure we have numeric scores
        group['score_num'] = pd.to_numeric(group['score'], errors='coerce')
        
        # Aggregate mean score per skill
        skill_scores = group.groupby('skillname')['score_num'].mean().reset_index()
        
        # Close the loop for radar chart
        skills = list(skill_scores['skillname'])
        scores = list(skill_scores['score_num'])
        if skills:
            skills.append(skills[0])
            scores.append(scores[0])
            
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=skills,
            fill='toself',
            name=f"{simname}"
        ))
        
    fig.update_layout(
        title="Skill Profile (Baseline)",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True
    )
    return fig

def plot_completion_donut(df):
    """Generates Donut chart for Completion Status."""
    if df is None or df.empty:
        return None

    # This usually comes from 'learner_engagement' where stat in ['Completed', 'In Progress', etc.]
    # We might need to filter for specific stats
    target_stats = ['Completed', 'In Progress', 'Registered']
    df_filtered = df[df['stat'].isin(target_stats)].copy()
    
    if df_filtered.empty:
        return None

    fig = make_subplots(rows=1, cols=len(df_filtered['simid'].unique()), 
                        subplot_titles=[f"Sim {sid}" for sid in df_filtered['simid'].unique()],
                        specs=[[{'type':'domain'}] * len(df_filtered['simid'].unique())])

    for i, (simid, group) in enumerate(df_filtered.groupby('simid')):
        fig.add_trace(go.Pie(
            labels=group['stat'], values=group['n'],
            hole=.4,
            name=f"Sim {simid}"
        ), row=1, col=i+1)
        
    fig.update_layout(title="Completion Status", annotations=[dict(text='Status', x=0.5, y=0.5, font_size=20, showarrow=False)])
    return fig

# -----------------------------------------------------------------------------
# Main Dashboard Generation
# -----------------------------------------------------------------------------

def generate_dashboard(data_dict, output_path):
    """
    Generate an HTML dashboard using Plotly.
    """
    logger.info("Generating Plotly dashboard...")
    
    figures = []
    
    # Extract DataFrames
    sim_dict = data_dict.get('sim', {})
    proj_dict = data_dict.get('proj', {})
    srv_dict = data_dict.get('srv', {})
    
    # 1. Learner Engagement
    if fig := plot_learner_engagement(sim_dict.get('learner_engagement')):
        figures.append(fig)

    # 2. Pass Rates
    if fig := plot_pass_rates(sim_dict.get('overall_pass_rates')):
        figures.append(fig)

    # 3. Engagement Over Time
    if fig := plot_engagement_over_time(proj_dict.get('proj_engagement_over_time')):
        figures.append(fig)
        
    # 4. NPS Scores
    if fig := plot_nps_scores(proj_dict.get('proj_nps')):
        figures.append(fig)
        
    # 5. Skill Polar Chart
    if fig := plot_skill_polar_chart(sim_dict.get('skill_baseline')):
        figures.append(fig)

    # 6. Completion Donut
    if fig := plot_completion_donut(sim_dict.get('learner_engagement')):
        figures.append(fig)

    # Save to HTML
    logger.info(f"Saving dashboard to {output_path}...")
    with open(output_path, 'w') as f:
        f.write('<html><head><script src="https://cdn.plot.ly/plotly-latest.min.js"></script></head><body>')
        f.write('<h1 style="text-align:center; font-family:sans-serif;">Simulation Dashboard (Plotly POC)</h1>')
        
        for fig in figures:
            f.write(fig.to_html(full_html=False, include_plotlyjs=False))
            f.write('<hr>')
            
        f.write('</body></html>')
    logger.info("Done.")


# Project dictionary
dict_project = {
    (86, 87): 'Our Code: We Respect One Another'}

# Save output file in same directory as this script
script_path = os.path.realpath(__file__)
script_dir = os.path.dirname(script_path)
OUTPUT_FILE = os.path.join(script_dir, 'dashboard.html')
output_file_pkl = os.path.join(script_dir, "data.pkl")

def run_report_workflow(
    customer="mckinsey.skillsims.com",
    s3_bucket="etu.appsciences",
    sim_ids=[55, 57],
    local_data_dir=None,
    use_local_pickle=False
):
    # Default dates (can be dynamic)
    START_DATE = '2024-01-01' 
    END_DATE = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    data = None

    # Option A: Load from local pickle (for intern/local dev)
    if use_local_pickle:
        pickle_path = os.path.join(script_dir, 'data.pkl')
        if os.path.exists(pickle_path):
            logger.info(f"Loading data from local pickle: {pickle_path}")
            try:
                with open(pickle_path, 'rb') as f:
                    data = pickle.load(f)
                logger.info("Data loaded successfully from pickle.")
            except Exception as e:
                logger.error(f"Failed to load pickle: {e}")
        else:
            logger.warning(f"Local pickle not found at {pickle_path}. Falling back to S3 extraction if possible.")

    # Option B: S3 Extraction
    if data is None:
        logger.info(f"Generating report for {customer} (Sims: {sim_ids})")
        
        # Initialize Pipeline
        pipeline = ParquetPipeline(
            s3_bucket=s3_bucket, 
            customer=customer,
            local_data_dir=local_data_dir
        )
        
        # 1. Get Base Demographics
        df_demog = get_base_demographics_from_parquet(pipeline, sim_ids)
        
        # 2. Load Client Demographics Excel
        logger.info("Loading Client Demographics Excel...")
        script_dir_abs = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(os.path.dirname(script_dir_abs), 'code_simulation_3_demographic_data.xlsx')

        list_client = []
        df_client = pd.DataFrame()

        try:
            if os.path.exists(file_path):
                logger.info(f"Found file at {file_path}. Loading...")
                client_data = pd.read_excel(file_path, converters={'username': str, 'uid': str}, keep_default_na=False)
                list_client.append(client_data)
            else:
                logger.error(f"File not found at {file_path}")
        except Exception as e:
            logger.error(f"Error reading file: {e}")

        if list_client:
            df_client = pd.concat(list_client, ignore_index=True)\
            .assign(uid = lambda x: x.apply(lambda y: str(y['User ID']) if pd.notnull(y['User ID']) else None, axis=1))\
            .filter(['uid', 'Region', 'Category', 'Band'])\
            .rename(columns={'Band':'Impact Band'})

        # 3. Merge Demographics
        if not df_demog.empty and not df_client.empty:
            if 'uid' in df_demog.columns: df_demog['uid'] = df_demog['uid'].astype(str)
            if 'uid' in df_client.columns: df_client['uid'] = df_client['uid'].astype(str)
            df_demog_merged = df_demog.merge(df_client, how='inner', on=['uid'])
        else:
            df_demog_merged = df_demog

        # 4. Transform Data
        dict_project = {tuple(sim_ids): 'Our Code: We Respect One Another'}
        ec2_customer = customer if '.' in customer else f"{customer}.skillsims.com"
        ec2_id, ec2_region = find_ec2(ec2_customer)
        
        data = get_transformed_data_from_parquet(
            pipeline=pipeline,
            sim_ids=sim_ids,
            start_date=START_DATE,
            end_date=END_DATE,
            df_demog=df_demog_merged,
            dict_project=dict_project,
            ec2_id=ec2_id,
            ec2_region=ec2_region,
            s3_bucket_name='etu.appsciences',
            s3_region='us-east-1'
        )

    if not data:
        logger.error("No data available. Exiting.")
        return

    # Generate Dashboard
    generate_dashboard(data, OUTPUT_FILE)


if __name__ == '__main__':
    # Check for local flag argument
    use_local = '--local' in sys.argv or os.path.exists(os.path.join(os.path.dirname(__file__), 'data.pkl'))
    
    run_report_workflow(
        customer="mckinsey.skillsims.com",
        s3_bucket="etu.appsciences",
        sim_ids=[86, 87],
        local_data_dir=None,
        use_local_pickle=use_local
    )
