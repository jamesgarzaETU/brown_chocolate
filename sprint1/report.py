# ***************************************************************************
# Description: Set of functions to build a dashboard
#
#              Functions included:
#              -------------------
#              find_ec2:      Find a running AWS EC2 ID and Region for a client
#
#              find_rds:      Find an RDS ID and region for a client
#
#              find_s3:       Find an S3 bucket name and region for a client
#
#              aws_resources: Get list of all available client AWS resources (EC2, RDS and S3)
#
#              sshtunnel:     Open an SSH tunnel into a client server
#
#              client_connect: Connect to Client Server using Paramiko
#
#              stringcleaner: Cleans a string of strange characters (used in xml_to_df function)
#
#              xml_to_df:     Converts an XML file into a dataframe
#
#              sim_levels:     Defines decision levels of a sim using data from its XML
#
#              rgb_scale:      Creates colour scale between 2 RGB colours
#
#              extract_data:   Extract and summarize the data from Sims in standardized formats
#
#              report:         Takes results from extract_data and creates a Dashboard HTML file
#
# Programmer:    Martin McSharry
# Creation Date: 18-Feb-2024
# ---------------------------------------------------------------------------
# Revision History
#
# Revision Date:
# Programmer:
# Revision:
# ***************************************************************************/


import numpy as np
import pandas as pd
import pymysql
import paramiko
import json
import boto3
from datetime import date, timedelta, datetime
import time
import html
from sshtunnel import SSHTunnelForwarder

def get_js_content(filename):
	"""Reads and returns the content of a JS file from the original_dahsboard directory."""
	import os
	# Look in original_dahsboard first, then current dir
	paths_to_check = [
		os.path.join(os.path.dirname(__file__), 'original_dahsboard', filename),
		os.path.join(os.path.dirname(__file__), filename)
	]
	
	for path in paths_to_check:
		if os.path.exists(path):
			try:
				with open(path, 'r', encoding='utf-8') as f:
					return f.read()
			except Exception as e:
				print(f"Error reading {path}: {e}")
				return f"// Error reading {filename}"
	
	return f"// File not found: {filename}"
import re
import xml.etree.ElementTree as ET
import lxml.html
import unicodedata
import math
import os
import shutil
from subprocess import call
import json
import plotly.express as px


# ------------------------------------------------->
# ----- Helper function for Plotly Express charts ->
# ------------------------------------------------->

def create_proj_engagement_chart(df, project_name):
	"""
	Creates a horizontal bar chart for Learner Engagement by Simulation using Plotly Express.

	Args:
		df (pandas.DataFrame): The proj_engagement DataFrame
		project_name (str): The project name to filter by

	Returns:
		tuple: (chart_json, summary_html) - JSON string with Plotly data/layout and HTML for summary
	"""
	import json as json_module

	# Filter data for the selected project
	filtered_df = df[df['project'].str.strip() == project_name.strip()].copy()

	if filtered_df.empty:
		return None, "<p>No data available for the selected project.</p>"

	# Get summary stats from first row
	first_row = filtered_df.iloc[0]
	total = int(first_row['total'])
	pct_all = first_row['pct_all_complete']
	tot_all = int(first_row['total_all_complete'])

	# Create summary HTML
	summary_html = f'''
	<p class="component_text">
		<span style="font-weight:700">{total:,}</span>
		<span style="font-weight:400"> learners have completed an attempt of </span>
		<span style="font-weight:700">at least one </span>
		<span style="font-weight:400">Simulation.</span><br>
		<span style="font-weight:700">{pct_all:.1f}% ({tot_all:,})</span>
		<span style="font-weight:400"> of learners have completed </span>
		<span style="font-weight:700">all </span>
		<span style="font-weight:400">Sims.</span>
	</p>
	'''

	# Create text column for bar labels
	filtered_df['text_label'] = filtered_df.apply(
		lambda row: f"{int(row['n']):,} ({row['pct']:.1f}%)", axis=1
	)

	# Sort by sim_order for consistent display
	filtered_df = filtered_df.sort_values('sim_order', ascending=True)

	# Create horizontal bar chart
	fig = px.bar(
		filtered_df,
		x='n',
		y='simname',
		orientation='h',
		color='stat',
		text='text_label',
		labels={
			'n': 'Number of Learners',
			'simname': 'Simulation',
			'stat': 'Status'
		},
		color_discrete_map={stat: filtered_df[filtered_df['stat'] == stat]['bar_color'].iloc[0]
						   for stat in filtered_df['stat'].unique()}
	)

	# Update layout
	fig.update_layout(
		height=max(300, len(filtered_df['simname'].unique()) * 80 + 100),
		margin=dict(l=20, r=20, t=30, b=50),
		yaxis=dict(autorange='reversed'),  # Top-down reading order
		legend=dict(
			orientation='h',
			yanchor='bottom',
			y=1.02,
			xanchor='center',
			x=0.5
		),
		font=dict(family='Open Sans, sans-serif'),
		showlegend=True,
		barmode='group'
	)

	# Update bar text position
	fig.update_traces(textposition='outside')

	# Return JSON data for JavaScript to render with Plotly.newPlot()
	# Manually build dict with plain Python lists to avoid binary array encoding
	import numpy as np

	def numpy_to_python(obj):
		"""Recursively convert numpy types and Plotly objects to Python native types"""
		if obj is None:
			return None
		elif isinstance(obj, np.ndarray):
			return [numpy_to_python(x) for x in obj.tolist()]
		elif isinstance(obj, (np.integer,)):
			return int(obj)
		elif isinstance(obj, (np.floating,)):
			return float(obj)
		elif isinstance(obj, (bool, int, float, str)):
			return obj
		elif hasattr(obj, 'to_plotly_json'):
			# Handle Plotly objects (like ErrorX, Marker, etc.)
			return numpy_to_python(obj.to_plotly_json())
		elif isinstance(obj, dict):
			return {k: numpy_to_python(v) for k, v in obj.items()}
		elif isinstance(obj, (list, tuple)):
			return [numpy_to_python(x) for x in obj]
		return obj

	# Build data array from traces
	data_list = []
	for trace in fig.data:
		trace_dict = {}
		for key in trace:
			val = trace[key]
			trace_dict[key] = numpy_to_python(val)
		data_list.append(trace_dict)

	# Get layout as dict
	layout_dict = numpy_to_python(fig.layout.to_plotly_json())

	chart_dict = {'data': data_list, 'layout': layout_dict}
	chart_json = json_module.dumps(chart_dict)

	return chart_json, summary_html


# ------------------------------------------------->
# ----- Function for creating the HTML Report ----->
# ------------------------------------------------->



def report(
	dict_df,
	start_date,
	end_date,
	dict_project=None,
	survey_comment_limit=None,
	demog_filters=None,
	mckinsey=False,
	):
	"""
	Generates an HTML report from the extracted and summarized data.

	Args:
		dict_df (dict): A dictionary containing the extracted and summarized data.
		start_date (str): The start date for the data included in the report.
		end_date (str): The end date for the data included in the report.
		dict_project (dict, optional): Dictionary linking multiple Sim IDs to project(s). This will create data for the "Course Summary" tab of the dashboard. Defaults to None.
		survey_comment_limit (int, optional): Integer to limit the number of comments from each free-text question. Defaults to None.
		demog_filters (pandas.DataFrame, optional): DataFrame containing demographic filters. Defaults to None.
		mckinsey (bool, optional): Flag to indicate if the report is for McKinsey. Defaults to False.

	Returns:
		str: The generated HTML report as a string.
	"""
  
	if mckinsey:
		html_page = '''
			<!DOCTYPE html>
			<html xmlns="http://www.w3.org/1999/xhtml">

				<head>
					<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
					<meta name="viewport" content="width=device-width, initial-scale=1" />
					<meta name="description" content="Immersive Simulator. Emulate real-world situations for learners to apply skills, retain knowledge and accelerate lasting behavior change. The powerful and intuitive platform interface engages learners and makes learning stick." />
					<link rel="shortcut icon" href="https://marketplace.skillsims.com/etu/resources/images/etu_icon.png" type="image/x-icon" />
					
					<title>Skillwell - Auto Insights Report</title>
					<link type="text/css" rel="stylesheet" href="report-style-skillwell.css" />
					<link href="https://fonts.googleapis.com/css?family=Open+Sans:400,300,700" rel="stylesheet" type="text/css" />

					<!-- JS & CHART LIBRARY -->
					<script type = "text/javascript" src="d3.v7.min.js"></script>
					<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>

					<!-- Inline Custom JS -->
					<script type="text/javascript">
					''' + get_js_content('chart_bar_horizontal.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('chart_bar_vertical_character.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('chart_donut.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('chart_line.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('chart_polar_mckinsey.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('createFilterData.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('chart_drag_drop.js') + '''
					</script>
					<script type="text/javascript">
					''' + get_js_content('createSummaryData.js') + '''
					</script>
				</head>

			'''
	else:
			html_page = '''
		<!DOCTYPE html>
		<html xmlns="http://www.w3.org/1999/xhtml">

			<head>
				<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
				<meta name="viewport" content="width=device-width, initial-scale=1" />
				<meta name="description" content="Immersive Simulator. Emulate real-world situations for learners to apply skills, retain knowledge and accelerate lasting behavior change. The powerful and intuitive platform interface engages learners and makes learning stick." />
				<link rel="shortcut icon" href="https://marketplace.skillsims.com/etu/resources/images/etu_icon.png" type="image/x-icon" />
				
				<title>Skillwell - Auto Insights Report</title>
				<link type="text/css" rel="stylesheet" href="report-style-skillwell.css" />
				<link href="https://fonts.googleapis.com/css?family=Open+Sans:400,300,700" rel="stylesheet" type="text/css" />

				<!-- JS & CHART LIBRARY -->
				<script type = "text/javascript" src="d3.v7.min.js"></script>
				<script src="plotly-2.27.0.min.js"></script>
				<script type = "text/javascript" src="chart_bar_horizontal.js"></script>
				<script type = "text/javascript" src="chart_bar_vertical_character.js"></script>
				<script type = "text/javascript" src="chart_donut.js"></script>
				<script type = "text/javascript" src="chart_line.js"></script>
				<script type = "text/javascript" src="chart_polar.js"></script>
				<script type = "text/javascript" src="createFilterData.js"></script>
				<script type = "text/javascript" src="chart_drag_drop.js"></script>
				<script type = "text/javascript" src="createSummaryData.js"></script>
			</head>

		'''

	html_page += '''
	<body class="main">

		<div class="main-container">

			<div class="wrapper">

				<header id="headerDiv" class="head hideprint">
					<div id="headerContentNew" class="container">
						<div class="top">
							<div class="nav-logo highcontrastcolor">
								<div class="image"><img id="logoUoF" src="https://s3-eu-west-1.amazonaws.com/etu.static.content/skillwelllogoemail.png" alt="Skillwell Logo" role="img" aria-label="Skillwell Logo"/><span class="hiddenmaintext" aria-hidden="true">Skillwell Logo</span>								
								</div>
							</div>
							<div class="top-links">
								<div class="head-actions">
									<strong class="marginright5">Select Course: </strong>
									<select class="proj_filter" id="selectProj">
									</select>
									<script type="application/json" data-for="selectProj" data-nonempty="">{}</script>
								</div>
							</div>
						</div>
					</div>
				</header>
				<main id="content" name="wrapper" class="content-area">
					<div class="outcome-report">
												<div class="head-outcome">
							<div class="title">
								
								<h1 class="mainreportname">
									<a href="#" onclick="printOutcomePage();" class="printlink">Print</a>
									Auto Insights Report
								</h1>

							</div>
						</div>

						<nav class="tabs-module" id="reportNavigation" aria-label="Secondary">
							<div class="justoutline w100p">
								<div class="scrollmenuelement">
									<ul class="wrapper-2" id="outcomeMenuContainerList" style="left: 0px;">
										<li class="tab-wrapper">
											<a id="multisim_lnk" href="#" class="tab-name selected" role="button" tabindex="0" aria-label="Multi-sim Summary" onclick="openTab(event, 'multisim_data')">
												Multi-sim Summary
											</a>
										</li>
										<li class="tab-wrapper">
											<a id="summary_lnk" href="#" class="tab-name" role="button" tabindex="0" aria-label="Sim Summary" onclick="openTab(event, 'sim_data')">
												Sim Summary
											</a>
										</li>
										<li class="tab-wrapper">
											<a id="survey_lnk" href="#" class="tab-name" role="button" tabindex="0" aria-label="Survey Results" onclick="openTab(event, 'srv_data')">
												Survey Results
											</a>
										</li>
	'''

	# Add demographics tab conditionally - create it here before adding to HTML
	demog_tab_html_early = '''
										<li class="tab-wrapper">
											<a id="demographics_lnk" href="#" class="tab-name" role="button" tabindex="0" aria-label="Demographics Results" onclick="openTab(event, 'dmg_data')">
												Demographics
											</a>
										</li>''' if len(dict_df.get('dmg', [])) > 0 else ''

	html_page += demog_tab_html_early

	html_page += '''
									</ul>
								</div>
							</div>
						</nav>

	'''

	# Top Menu Items
	hovered_num = 0
	for key in dict_df:

		if len(dict_df[key]) > 0:
			hovered_num += 1

		hovered = 'id="{0}" class="hovered"'.format(key) if hovered_num == 1 else 'id="{0}"'.format(key)

		if key == 'proj':
			proj_menu = '''
			<li {0}>
				<a href="#" onclick="openTab(event, 'multisim_data')">
					<span class="icon" style="fill:white;">
						<svg width='30px' style="padding: 15 0px;" viewBox="0 0 576 512"><path d="M320 32c-8.1 0-16.1 1.4-23.7 4.1L15.8 137.4C6.3 140.9 0 149.9 0 160s6.3 19.1 15.8 22.6l57.9 20.9C57.3 229.3 48 259.8 48 291.9v28.1c0 28.4-10.8 57.7-22.3 80.8c-6.5 13-13.9 25.8-22.5 37.6C0 442.7-.9 448.3 .9 453.4s6 8.9 11.2 10.2l64 16c4.2 1.1 8.7 .3 12.4-2s6.3-6.1 7.1-10.4c8.6-42.8 4.3-81.2-2.1-108.7C90.3 344.3 86 329.8 80 316.5V291.9c0-30.2 10.2-58.7 27.9-81.5c12.9-15.5 29.6-28 49.2-35.7l157-61.7c8.2-3.2 17.5 .8 20.7 9s-.8 17.5-9 20.7l-157 61.7c-12.4 4.9-23.3 12.4-32.2 21.6l159.6 57.6c7.6 2.7 15.6 4.1 23.7 4.1s16.1-1.4 23.7-4.1L624.2 182.6c9.5-3.4 15.8-12.5 15.8-22.6s-6.3-19.1-15.8-22.6L343.7 36.1C336.1 33.4 328.1 32 320 32zM128 408c0 35.3 86 72 192 72s192-36.7 192-72L496.7 262.6 354.5 314c-11.1 4-22.8 6-34.5 6s-23.5-2-34.5-6L143.3 262.6 128 408z"/></svg>
					</span>
					<span class="title" style="font-weight:bold;">Course Summary</span>
				</a>
			</li>
			'''.format(hovered) if len(dict_df[key]) > 0  else ''

			proj_show_hide = "grid" if hovered_num == 1 else 'none'


		if key == 'sim':
			sim_menu = '''
			<li {0}>
				<a href="#" onclick="openTab(event, 'sim_data')">
					<span class="icon" style="fill:white;">
						<svg width='30px' style="padding: 15 0px;" viewBox="0 0 576 512"><path d="M0 80C0 53.49 21.49 32 48 32H144C170.5 32 192 53.49 192 80V96H384V80C384 53.49 405.5 32 432 32H528C554.5 32 576 53.49 576 80V176C576 202.5 554.5 224 528 224H432C405.5 224 384 202.5 384 176V160H192V176C192 177.7 191.9 179.4 191.7 180.1L272 288H368C394.5 288 416 309.5 416 336V432C416 458.5 394.5 480 368 480H272C245.5 480 224 458.5 224 432V336C224 334.3 224.1 332.6 224.3 331L144 224H48C21.49 224 0 202.5 0 176V80z"/></svg>
					</span>
					<span class="title" style="font-weight:bold;">Sim Summary</span>
				</a>
			</li>
			'''.format(hovered) if len(dict_df[key]) > 0  else ''

			sim_show_hide = "grid" if hovered_num == 1 else 'none'


		if key == 'srv':
			survey_menu = '''
			<li {0}>
			<a href="#" onclick="openTab(event, 'srv_data')">
				<span class="icon" style="fill:white;">
					<svg width='30px' style="padding: 15 0px;" viewBox="0 0 512 512"><path d="M256 0C114.6 0 0 114.6 0 256s114.6 256 256 256s256-114.6 256-256S397.4 0 256 0zM256 464c-114.7 0-208-93.31-208-208S141.3 48 256 48s208 93.31 208 208S370.7 464 256 464zM256 336c-18 0-32 14-32 32s13.1 32 32 32c17.1 0 32-14 32-32S273.1 336 256 336zM289.1 128h-51.1C199 128 168 159 168 198c0 13 11 24 24 24s24-11 24-24C216 186 225.1 176 237.1 176h51.1C301.1 176 312 186 312 198c0 8-4 14.1-11 18.1L244 251C236 256 232 264 232 272V288c0 13 11 24 24 24S280 301 280 288V286l45.1-28c21-13 34-36 34-60C360 159 329 128 289.1 128z"/></svg>
				</span>
				<span class="title" style="font-weight:bold;">Survey Results</span>
			</a>
			</li>
			'''.format(hovered) if len(dict_df[key]) > 0  else ''

			survey_show_hide = "grid" if hovered_num == 1 else 'none'

		if key == 'dmg':
			demog_menu = '''
			<li {0}>
			  <a href="#" onclick="openTab(event, 'dmg_data')">
				<span class="icon" style="fill:white;">
				  <svg width='30px' style="padding: 15 0px;" viewBox="0 0 640 512"><path d="M319.9 320c57.41 0 103.1-46.56 103.1-104c0-57.44-46.54-104-103.1-104c-57.41 0-103.1 46.56-103.1 104C215.9 273.4 262.5 320 319.9 320zM369.9 352H270.1C191.6 352 128 411.7 128 485.3C128 500.1 140.7 512 156.4 512h327.2C499.3 512 512 500.1 512 485.3C512 411.7 448.4 352 369.9 352zM512 160c44.18 0 80-35.82 80-80S556.2 0 512 0c-44.18 0-80 35.82-80 80S467.8 160 512 160zM183.9 216c0-5.449 .9824-10.63 1.609-15.91C174.6 194.1 162.6 192 149.9 192H88.08C39.44 192 0 233.8 0 285.3C0 295.6 7.887 304 17.62 304h199.5C196.7 280.2 183.9 249.7 183.9 216zM128 160c44.18 0 80-35.82 80-80S172.2 0 128 0C83.82 0 48 35.82 48 80S83.82 160 128 160zM551.9 192h-61.84c-12.8 0-24.88 3.037-35.86 8.24C454.8 205.5 455.8 210.6 455.8 216c0 33.71-12.78 64.21-33.16 88h199.7C632.1 304 640 295.6 640 285.3C640 233.8 600.6 192 551.9 192z"/></svg>
				</span>
				<span class="title" style="font-weight:bold;">Demographics</span>
			  </a>
			</li>
			'''.format(hovered) if len(dict_df[key]) > 0  else ''

			demog_show_hide = "grid" if hovered_num == 1 else 'none'

	proj_filter = '''
	<div style="width: 300px; display:flex; justify-content:space-between;">
		<label class="control-label" for="selectProj" style="font-size: 14px; font-weight:bold; margin-top:15px;">Select Course: </label>
		<div>
			<select class="proj_filter" id="selectProj" style="font-size: 14px; width: 200px; height:80%; margin-top:5px;">
			</select>
			<script type="application/json" data-for="selectProj" data-nonempty="">{}</script>
		</div>
	</div>
	''' if dict_project is not None else ""


	if demog_filters is not None:

		dmg_filter = '''
		<div style="display:flex; justify-content:space-between;">
			<div style="width: 250px; display:{0}; justify-content:space-between;">
				<label class="control-label tabcontent multisim_data sim_data srv_data" for="selectDemogVar" style="font-size: 14px; font-weight:bold; margin-top:15px; display:none;">Demographic:</label>
				  <select class="demogvar_filter tabcontent multisim_data sim_data srv_data" id="selectDemogVar" style="font-size:14px; width:150px; height:80%; margin-top:5px;">
				  </select>
				  <script type="application/json" data-for="selectDemogVar" data-nonempty="">{{}}</script>
				</div>
			</div>

			<div style="width: 200px; display:flex; justify-content:space-between;">
				<label class="control-label tabcontent multisim_data sim_data srv_data" for="selectDemogVal" style="font-size: 14px; font-weight:bold; margin-top:15px;">{1}:</label>
				  <select class="demogval_filter tabcontent multisim_data sim_data srv_data" id="selectDemogVal" style="font-size:14px; width:150px; height:80%; margin-top:5px;">
				  </select>
				  <script type="application/json" data-for="selectDemogVar" data-nonempty="">{{}}</script>
			</div>
		</div>
		'''.format(
			'flex' if len(demog_filters['demog_var'].unique()) > 1 else 'none',
			'Value' if len(demog_filters['demog_var'].unique()) > 1 else demog_filters['demog_var'].unique()[0]
		)

	else:
		dmg_filter = ""

	sim_filter_display = "display:none;" if dict_project is not None else ""

	proj_header_display = "grid" if dict_project is not None else "none"
	sim_header_display = "none" if dict_project is not None else "grid"

	sim_list = list(dict_df['proj']['proj_sims']['simname'].unique())
	sim_list_html = ""
	for item in sim_list:
		sim_list_html += f"<li>{item}</li>"

	html_page += '''

		<!-- TOP MENU -->
		<div class="selectsubmenu sim_data srv_data dmg_data">
			<div class="fright">
				<strong class="marginright5">Select Simulation: </strong>
						<select class="sim_filter" id="selectSim">
						</select>
						<script type="application/json" data-for="selectSim" data-nonempty="">{{}}</script>
			</div>
		</div>

		<!-- Details -->
		<div class="tabcontent multisim_data" >
				<h2 class="onlyprint borderbottomplain marginbottom20">Details</h2>
				<div class="flexcontainerdiv borderbottom marginbottom50 paddingbottom30">
					<div class="flexcontentdiv">
						<p>
							Report generated: <strong>{13}</strong><br/>
							Data included: <strong>{14}</strong>
						</p>
					</div>

					<div class="flexcontentdiv">
							<h4>Simulations included</h4>
							<p>
							The following simulations are included in this report:

							<ul class="col100" style="display: {{11}};">
							{15}
							</ul>
							</p>
					</div>
			</div>
			 <div id="component_content_proj" class="left100" ></div>

			</div>  

				<!-- SINGLE SIM Summary:  copy for additional containers  --> 
				<div class="tabcontent sim_data" style="display:none;">
					<table id="component_content_sim">
					</table>
				</div>

				<!-- Survey: copy for additional containers  --> 
				<div class="tabcontent srv_data" style="display:none;">
					<table id="component_content_srv">
					</table>
				</div>

				<!-- Demographics: copy for additional containers  --> 
				<div class="tabcontent dmg_data" style="display:none;">
					<table id="component_content_dmg">
						<div id="component_dmg_filter" class="left100">
							<button class="collapsible" class="Regular">Data Filters</button>
							<div  class="left100 margintop20 collapse_content" id="component_content_dmg_filter_collapsible" style="overflow: hidden"></div>
						</div>
						<div id="component_content_dmg" class="left100 margintop20">
										</div>
					</table>
				</div>

		</div>
		<script type="text/javascript">

		//<![CDATA[

		function printOutcomePage() {{
			// Show modal with plot selection
			showPrintSelectionModal();
		}}

		function showPrintSelectionModal() {{
			// Create modal overlay
			const modal = document.createElement('div');
			modal.id = 'printModal';
			modal.style.cssText = `
				position: fixed;
				top: 0;
				left: 0;
				width: 100%;
				height: 100%;
				background: rgba(0,0,0,0.7);
				display: flex;
				justify-content: center;
				align-items: center;
				z-index: 10000;
			`;

			// Create modal content
			const modalContent = document.createElement('div');
			modalContent.style.cssText = `
				background: white;
				padding: 30px;
				border-radius: 8px;
				max-width: 600px;
				max-height: 80vh;
				overflow-y: auto;
			`;

			// Get all chart containers - use .rowdivider for actual chart sections
			const charts = document.querySelectorAll('.rowdivider.borderbottom');

			let modalHTML = `
				<h2>Select Plots to Print</h2>
				<p>Choose which plots you want to include in the printout:</p>
				<div style="margin: 20px 0;">
					<label style="display: block; margin-bottom: 10px;">
						<input type="checkbox" id="selectAllPlots" onchange="toggleAllPlots(this)">
						<strong>Select All</strong>
					</label>
					<hr>
					<label style="display: block; margin-bottom: 10px;">
						<strong>Plots per page:</strong>
						<select id="plotsPerPage" style="margin-left: 10px;">
							<option value="1">1 plot per page</option>
							<option value="2" selected>2 plots per page</option>
							<option value="3">3 plots per page</option>
							<option value="4">4 plots per page</option>
							<option value="all">All on one page</option>
						</select>
					</label>
					<hr>
			`;

			// Add checkbox for each chart - UNCHECKED by default
			charts.forEach((chart, index) => {{
				// Get the title from the h1 element inside the chart
				const chartTitle = chart.querySelector('h1')?.textContent ||
								chart.querySelector('h2, h3, h4')?.textContent ||
								chart.getAttribute('aria-label') ||
								`Chart ${{index + 1}}`;
				modalHTML += `
					<label style="display: block; margin: 8px 0;">
						<input type="checkbox" class="plot-checkbox" value="${{index}}">
						${{chartTitle.trim()}}
					</label>
				`;
			}});

			modalHTML += `
				</div>
				<div style="display: flex; gap: 10px; justify-content: flex-end;">
					<button onclick="closePrintModal()" style="padding: 10px 20px; cursor: pointer;">Cancel</button>
					<button onclick="executePrint()" style="padding: 10px 20px; cursor: pointer; background: #4285f4; color: white; border: none; border-radius: 4px;">Print Selected</button>
				</div>
			`;

			modalContent.innerHTML = modalHTML;
			modal.appendChild(modalContent);
			document.body.appendChild(modal);
		}}

		function toggleAllPlots(checkbox) {{
			document.querySelectorAll('.plot-checkbox').forEach(cb => {{
				cb.checked = checkbox.checked;
			}});
		}}

		function closePrintModal() {{
			document.getElementById('printModal')?.remove();
		}}

		function executePrint() {{
			// Get selected plots
			const selectedPlots = Array.from(document.querySelectorAll('.plot-checkbox:checked'))
				.map(cb => parseInt(cb.value));

			if (selectedPlots.length === 0) {{
				alert('Please select at least one plot to print.');
				return;
			}}

			const plotsPerPage = parseInt(document.getElementById('plotsPerPage').value) || 999;

			// Get all chart containers
			const allCharts = document.querySelectorAll('.rowdivider.borderbottom');

			// Store original styles and hide non-selected plots
			let printCounter = 0;
			allCharts.forEach((chart, index) => {{
				const computedDisplay = window.getComputedStyle(chart).display;
				const originalPageBreakAfter = chart.style.pageBreakAfter || '';
				const originalPageBreakBefore = chart.style.pageBreakBefore || '';
				const originalPageBreakInside = chart.style.pageBreakInside || '';

				chart.setAttribute('data-original-display', computedDisplay);
				chart.setAttribute('data-original-page-break-after', originalPageBreakAfter);
				chart.setAttribute('data-original-page-break-before', originalPageBreakBefore);
				chart.setAttribute('data-original-page-break-inside', originalPageBreakInside);

				// Remove any previous print classes
				chart.classList.remove('hide-for-print', 'print-selected');
				chart.removeAttribute('data-print-index');

				// Also store and reset h1 styles inside the chart
				const h1Element = chart.querySelector('h1');
				if (h1Element) {{
					const h1PageBreakBefore = h1Element.style.pageBreakBefore || '';
					const h1PageBreakAfter = h1Element.style.pageBreakAfter || '';
					chart.setAttribute('data-h1-page-break-before', h1PageBreakBefore);
					chart.setAttribute('data-h1-page-break-after', h1PageBreakAfter);
				}}

				if (!selectedPlots.includes(index)) {{
					chart.style.display = 'none';
					chart.classList.add('hide-for-print');
				}} else {{
					chart.classList.add('print-selected');
					chart.setAttribute('data-print-index', printCounter);

					// Override h1 page breaks that would force new pages
					if (h1Element) {{
						h1Element.style.pageBreakBefore = 'avoid';
						h1Element.style.pageBreakAfter = 'avoid';
					}}

					// Apply page break logic based on plots per page
					// First chart should never have page-break-before
					chart.style.pageBreakBefore = 'avoid';

					if (plotsPerPage === 1) {{
						// Every plot on new page
						chart.style.pageBreakAfter = 'always';
						// First one doesn't need break before
						if (printCounter > 0) {{
							chart.style.pageBreakBefore = 'always';
						}}
					}} else if (plotsPerPage === 999) {{
						// All on one page
						chart.style.pageBreakAfter = 'auto';
						chart.style.pageBreakBefore = 'auto';
					}} else {{
						// Multiple per page - break after every Nth selected plot
						if ((printCounter + 1) % plotsPerPage === 0) {{
							chart.style.pageBreakAfter = 'always';
						}} else {{
							chart.style.pageBreakAfter = 'auto';
						}}
						// Only first chart has no break before
						chart.style.pageBreakBefore = printCounter === 0 ? 'auto' : 'auto';
					}}

					// Always avoid breaking inside a chart
					chart.style.pageBreakInside = 'avoid';

					printCounter++;
				}}
			}});

			// Add print-specific class to body
			document.body.classList.add('custom-print-layout');
			document.body.setAttribute('data-plots-per-page', plotsPerPage);

			// Close modal
			closePrintModal();

			// Trigger print with a small delay to ensure DOM updates
			setTimeout(() => {{
				window.print();
			}}, 150);

			// Restore after printing
			const restoreDisplay = () => {{
				document.body.classList.remove('custom-print-layout');
				document.body.removeAttribute('data-plots-per-page');

				allCharts.forEach((chart) => {{
					const originalDisplay = chart.getAttribute('data-original-display') || 'block';
					const originalPageBreakAfter = chart.getAttribute('data-original-page-break-after') || '';
					const originalPageBreakBefore = chart.getAttribute('data-original-page-break-before') || '';
					const originalPageBreakInside = chart.getAttribute('data-original-page-break-inside') || '';

					chart.style.display = originalDisplay;
					chart.style.pageBreakAfter = originalPageBreakAfter;
					chart.style.pageBreakBefore = originalPageBreakBefore;
					chart.style.pageBreakInside = originalPageBreakInside;

					// Restore h1 styles
					const h1Element = chart.querySelector('h1');
					if (h1Element) {{
						const h1PageBreakBefore = chart.getAttribute('data-h1-page-break-before') || '';
						const h1PageBreakAfter = chart.getAttribute('data-h1-page-break-after') || '';
						h1Element.style.pageBreakBefore = h1PageBreakBefore;
						h1Element.style.pageBreakAfter = h1PageBreakAfter;
						chart.removeAttribute('data-h1-page-break-before');
						chart.removeAttribute('data-h1-page-break-after');
					}}

					chart.removeAttribute('data-original-display');
					chart.removeAttribute('data-original-page-break-after');
					chart.removeAttribute('data-original-page-break-before');
					chart.removeAttribute('data-original-page-break-inside');
					chart.removeAttribute('data-print-index');
					chart.classList.remove('hide-for-print');
					chart.classList.remove('print-selected');
				}});

				window.removeEventListener('afterprint', restoreDisplay);
			}};

			window.addEventListener('afterprint', restoreDisplay);
		}}

			function openTab(evt, tabName) {{
					var i, tabcontent, tablinks, dropdown;
					const submenu = document.querySelector('.selectsubmenu');
					if (submenu) {{
						submenu.style.display = 'none';
					}}

					tabcontent = document.getElementsByClassName("tabcontent");
					for (i = 0; i < tabcontent.length; i++) {{
						tabcontent[i].style.display = "none";
					}}
					tablinks = document.getElementsByClassName("tab-name");
					for (i = 0; i < tablinks.length; i++) {{
						tablinks[i].className = tablinks[i].className.replace(" selected", "");
					}}
					//document.getElementById(tabName).style.display = "grid";
					var tabnames = document.getElementsByClassName(tabName);
					for (i = 0; i < tabnames.length; i++) {{
						tabnames[i].style.display = "flex";
					}}
					evt.currentTarget.className += " selected";
					//evt.currentTarget.remove('active'));
					//evt.currentTarget.classList.add('selected');
			}}

			var body_font = "Open Sans, sans-serif";


			// Function to search through text in table
			function searchFunction(html_element) {{

			  filter = html_element.value.toUpperCase().split("&");

			  var regexTxt = "";
			  filter.forEach(function(v, i){{
				if(v.includes('^')){{
				  var string = '^((?!' + v.replace('^', '') + ').)*$'
				}}
				else{{
				  var string = v
				}}
				regexTxt += '(?=.*' + string + ')'
			  }})

			  id_num = html_element.id.split("_")[1];


			  var table = document.getElementById("table_" + id_num);
			  var tr = table.getElementsByTagName("tr");

			  // Loop through all table rows, and hide those who don't match the search query
			  numResults = 0;
			  for (i = 0; i < tr.length; i++) {{
				td = tr[i].getElementsByTagName("td")[0];
				if (td) {{
				  txtValue = td.textContent || td.innerText;
				  if (txtValue.toUpperCase().match(regexTxt)) {{
					tr[i].style.display = "";
					numResults += 1;
				  }} else {{
					tr[i].style.display = "none";
				  }}
				}}
			  }}

			  d3.select("#search_results_" + id_num).text(d3.format(",.0f")(numResults) + " Responses");
			}}

			// Integer/Decimal Format Function
			var formatInteger = d3.format(",");
			var formatDecimal = d3.format(",.1f");
			function numFormat(number){{
				return !(number % 1) ? formatInteger(number) : formatDecimal(number)
			}}

			// Function to get distinct rows based on specified columns
			function getDistinctRows(data, columns) {{
			  const seen = new Set();
			  return data.filter(row => {{
				// Create a key that uniquely identifies a combination of the specified columns
				const key = columns.map(col => row[col]).join('|');
				if (seen.has(key)) {{
				  return false;
				}} else {{
				  seen.add(key);
				  return true;
				}}
			  }});
			}}


	'''.format(
		proj_menu,
		sim_menu,
		survey_menu,
		demog_menu,

		"grid", #proj_show_hide,
		"grid", #sim_show_hide,
		"grid", #survey_show_hide,
		"grid", #demog_show_hide,

		proj_filter,
		sim_filter_display,
		dmg_filter,

		proj_header_display,
		sim_header_display,

		date.today().strftime("%b %-d, %Y"),
		datetime.strptime(start_date, "%Y-%m-%d").strftime("%b %-d, %Y") + ' - ' + datetime.strptime(end_date, "%Y-%m-%d").strftime("%b %-d, %Y"),
		sim_list_html,
	)


	# Add DIVs to page
	dict_component_title = {
		"learner_engagement"           : "Learner Engagement",
		"learner_engagement_over_time" : "Learner Engagement over Time",
		"overall_pass_rates"           : "Overall Pass Rates",
		"skill_pass_rates"             : "Skill Pass Rates",
		"skill_baseline"               : "Skill Performance Baseline",
		"skill_improvement"            : "Skill Performance Improvement",
		"decision_levels"              : "Decision Level Summary",
		"behaviors"                    : "Learner Behaviors and Decisions",
		"time_spent"                   : "Time Spent in Task Mode",
		"practice_mode"                : "Practice Mode",
		"knowledge_check_1"            : "Knowledge Check",

		"survey_responses"             : "Survey Responses",

		"proj_engagement"              : "Learner Engagement by Simulation",
		"proj_engagement_over_time"    : "Learner Engagement over Time by Simulation",
		"proj_performance_comparison_sim" : "Overall Performance Comparison of Simulations",
		"proj_learner_counts_comparison_sim" : "Learner Counts Comparison of Simulations",
		"proj_overall_pass_rates"      : "Overall Pass Rates by Simulation",
		"proj_skill_pass_rates"        : "Skill Pass Rates by Simulation",
		"proj_time_spent"              : "Time Spent in Task Mode by Simulation",
		"proj_practice_mode"           : "Practice Mode by Simulation",
		"proj_shared_skill_bar"        : "Performance in Shared Skills across Simulations",
		"proj_shared_skill_polar"      : "Performance in Shared Skills across Simulations",
		"proj_nps"                     : "NPS Score by Simulation",
		"proj_seat_time"               : "Seat-Time Savings",


		"dmg_engagement"               : "Learner Engagement",
		"dmg_skill_baseline"           : "Skill Performance Baseline",
		"dmg_decision_levels"          : "Decision Level Summary",

		"dmg_learner_counts"           : "Learner Counts by Demographic",
		"dmg_skill"                    : "Skill Performance by Demographic",
		"dmg_shared_skill"             : "Performance in Shared Skills across Simulations by Demographic",
	}


	# Append section for each component
	for i, key1 in enumerate(dict_df):
		if len(dict_df[key1]) > 0:
			for key2 in dict_df[key1]:
				if key2 != "sims" and key2 not in ["sims", "proj_sims", "knowledge_check_2", "dmg_vars"]:

					#top = '''.style("margin-top", "60px");''' if key2 in ("learner_engagement", "proj_engagement", "survey", "dmg_learner_counts") else ';'

					html_page += '''
					// Append div to html page to render chart in
					d3.select("#component_content_{1}")
					  .append("div")
					  .attr("class", "rowdivider borderbottom")
					  .attr("id", "component_content_{0}")
					  {3}


					d3.select("#component_content_{0}")
					  .append("h1")
					  .style("font-weight", 700)
					  //.style("color", "#335AA9")
					  .text("{2}");


					/*
					d3.select("#component_content_{0}")
					  .append("button")
					  .attr("class", "collapsible")
					  .style("font-weight", 700)
					  .text("{2}");

					d3.select("#component_content_{0}")
					  .append("div")
					  .attr("class", "collapse_content")
					  .attr("id", "component_content_{0}_collapsible");
					 */



					'''.format(
						key2,
						key1,
						dict_component_title.get(key2),
						";", #top
					)





	# Add data to page
	for key1 in dict_df:
		if key1 == "dmg":
			if len(dict_df[key1]) > 0:
				for i_key2, key2 in enumerate(dict_df[key1]):

					if key2 == "dmg_vars":
						html_page += '''
							var data_component_{0} = {1};

						'''.format(
							key2,
							dict_df[key1][key2].to_json(orient='records', indent=1)
						)

					else:

						if i_key2 == 1:
							html_page += '''
								var data_component_dmg = {
							'''

						html_page += '''
							"{0}": {{ "dataSemi":{1} }},
						'''.format(
							key2,
							dict_df[key1][key2].to_json(orient='records', indent=1)
						)

						if i_key2 == (len(dict_df[key1])-1):
							html_page += '''
								};

							'''

		else:
			if len(dict_df[key1]) > 0:
				for key2 in dict_df[key1]:

					html_page += '''
						var data_component_{0} = {1};

					'''.format(
						key2,
						dict_df[key1][key2].to_json(orient='records', indent=1)
					)



	# Add Project Selector (if required)
	if len(dict_df['proj']) > 0:

		html_page += '''

		// ----- List of all Projects ----->
		var projs = Array.from(new Set(data_component_proj_sims.map(d => d['project'])));
		projSelector = document.querySelector('.proj_filter');
		for(projEntry in projs){
			var currentOption = document.createElement('option');
			currentOption.text = projs[projEntry];
			projSelector.appendChild(currentOption);
		}

		'''

	# Fill in Sim Selector
	html_page += '''

	// ----- List of all Sims ----->
	var sims = Array.from(new Set(data_component_sims.map(d => d['simname'])));
	simSelector = document.querySelector('.sim_filter');

	'''



	# Add Demographic Selector (if required)
	if demog_filters is not None:

		html_page += '''

		// ----- Add options to Demographic Variable Selector ----->
		var demogs = {0};

		var demogvarSelector = document.querySelector('.demogvar_filter');

		for( demogsEntry in Array.from(new Set(demogs.map(d => d['demog_var']))) ){{
			var currentOption = document.createElement('option');
			currentOption.text = Array.from(new Set(demogs.map(d => d['demog_var'])))[demogsEntry];
			demogvarSelector.appendChild(currentOption);
		}}


		// ----- Add options to Demographic Value Selector ----->
		var demogvalSelector = document.querySelector('.demogval_filter');

		for( demogsEntry in demogs.filter(d => d['demog_var'] == demogs.map(d => d['demog_var'])[0] ).map(d => d['demog_val']) ){{
			var currentOption = document.createElement('option');
			currentOption.text = demogs.filter(d => d['demog_var'] == demogs.map(d => d['demog_var'])[0] ).map(d => d['demog_val'])[demogsEntry];
			demogvalSelector.appendChild(currentOption);
		}}


		/*
		// ----- List of all Demographic variables ----->
		var demogs = Array.from(new Set(data_component_dmg_vars.map(d => d['demog_var'])));
		demogSelector = document.querySelector('.demogvar_filter');
		for(demogEntry in demogs){{
			var currentOption = document.createElement('option');
			currentOption.text = demogs[demogEntry];
			demogSelector.appendChild(currentOption);
		}}
		*/

		'''.format(demog_filters.filter(['demog_var', 'demog_val']).drop_duplicates().to_json(orient='records', indent=1))




	# Add Demographic code (if required)
	if len(dict_df['dmg']) > 0:

		html_page += '''
			var filters = Array.from(new Set(data_component_dmg_vars.map(d => d["demog_var"])));
			var selected_filter = filters[0];
			var dataFilter = createFilterData(data_component_dmg_vars.filter(d => d["demog_val"] != null));

			// --- Demographics Filter Grid --->
			var filter_canvas_width = 333;

			if(filters.length % 3 == 0){

				var thisFilter = 1;

				for(let iRow = 1; iRow <= (filters.length/3); iRow++){
					d3.select("#component_content_dmg_filter_collapsible")
					  .append("div")
					  .attr("class", "grid")
					  .attr("id", "contentsub_dmg_filter_" + iRow)
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content")
					  .style("grid-template-columns", "1fr 1fr 1fr")
					  .style("grid-gap", "5px")
					  .style("margin-bottom", "20px");

					for(let iFilter = 1; iFilter <= 3; iFilter++){
						d3.select("#contentsub_dmg_filter_" + iRow).append("div").attr("id", "chart_dmg_filter_" + thisFilter).style("align-self", "start");
						thisFilter += 1;
					}
				}
			}
			else if(filters.length % 2 == 0){

				filter_canvas_width = 500;

				var thisFilter = 1;

				for(let iRow = 1; iRow <= (filters.length/2); iRow++){
					d3.select("#component_content_dmg_filter_collapsible")
					  .append("div")
					  .attr("class", "grid")
					  .attr("id", "contentsub_dmg_filter_" + iRow)
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content")
					  .style("grid-template-columns", "1fr 1fr")
					  .style("grid-gap", "5px")
					  .style("margin-bottom", "20px");

					for(let iFilter = 1; iFilter <= 2; iFilter++){
						d3.select("#contentsub_dmg_filter_" + iRow).append("div").attr("id", "chart_dmg_filter_" + thisFilter).style("align-self", "start");
						thisFilter += 1;
					}
				}
			}
			else{
				var thisFilter = 1;

				for(let iRow = 1; iRow <= Math.ceil(filters.length/3); iRow++){
					d3.select("#component_content_dmg_filter_collapsible")
					  .append("div")
					  .attr("class", "grid")
					  .attr("id", "contentsub_dmg_filter_" + iRow)
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content")
					  .style("grid-template-columns", (iRow == Math.ceil(filters.length/3))? ((filters.length % 3 == 1)? "1fr 1fr 1fr":"0.5fr 1fr 1fr 0.5fr"): "1fr 1fr 1fr")
					  .style("grid-gap", "5px")
					  .style("margin-bottom", "20px");

					if(iRow == Math.ceil(filters.length/3)){
						d3.select("#contentsub_dmg_filter_" + iRow).append("div").style("align-self", "end");
						for(let iFilter = 1; iFilter <= (filters.length % 3); iFilter++){
							d3.select("#contentsub_dmg_filter_" + iRow).append("div").attr("id", "chart_dmg_filter_" + thisFilter).style("align-self", "start");
							thisFilter += 1;
						}
					}
					else{
						for(let iFilter = 1; iFilter <= 3; iFilter++){
							d3.select("#contentsub_dmg_filter_" + iRow).append("div").attr("id", "chart_dmg_filter_" + thisFilter).style("align-self", "start");
							thisFilter += 1;
						}
					}
				}
			}


			// --- Create demographic filters --->
			dataFilter.forEach(function(vFil, iFil){

				chart_drag_drop(
					data=dataFilter[iFil],
					html_id="#chart_dmg_filter_" + (iFil+1),

					selected=(iFil == 0)? true: false,

					data_plot=null,

					values={var:"value", size:14, weight:700, order:'as_appear', ascending:true},

					title={value:[
					  {size:20, weight:700, text:filters[iFil]}
					], line:false},

					clr={
					  var:'clr',
					  palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
					  value:'#e32726'
					},

					font={family:body_font},

					margin={top:10, bottom:10, left:10, right:10, g:10},

					canvas={width:filter_canvas_width},
				);

			});

		'''






	for key1 in dict_df:

		if key1 in ["sim", "srv", "dmg"]:
			selector = "simSelector"
		else:
			selector = "projSelector"

		if len(dict_df[key1]) > 0:

			# Add updateGraphs_sim function to page
			html_page += '''
			function updateGraphs_{0}(){{
				var projSelector = document.getElementById("selectProj");

				if({1}.value != ""){{

			'''.format(key1, selector)


			proj_selector = 'd["project"] == projSelector.value && ' if dict_project is not None else ''

			dmg_selector = 'd["demog_var"] == demogvarSelector.value && d["demog_val"] == demogvalSelector.value && ' if demog_filters is not None else ''


			for key2 in dict_df[key1]:
				if key2 == 'learner_engagement':
					html_page += '''
					// LEARNER ENGAGEMENT (Vanilla JS + Plotly)
					try {{
						var parent = document.getElementById("component_content_learner_engagement");
						var existing = document.getElementById("contentsub_learner_engagement");
						if (existing && parent) parent.removeChild(existing);

						var grid = document.createElement("div");
						grid.id = "contentsub_learner_engagement";
						grid.style.display = "grid";
						grid.style.gridTemplateRows = "min-content min-content";
						grid.style.gridTemplateColumns = "1fr 1fr";
						grid.style.gridGap = "5px";
						grid.style.marginBottom = "20px";
						if (parent) parent.appendChild(grid);

						var ids = [
							"text_component_learner_engagement_1",
							"text_component_learner_engagement_2",
							"chart_component_learner_engagement_1",
							"chart_component_learner_engagement_2"
						];

						var styles = ["end", "end", "start", "start"];

						ids.forEach((id, i) => {{
							var div = document.createElement("div");
							div.className = "grid__item";
							div.id = id;
							div.style.alignSelf = styles[i];
							grid.appendChild(div);
						}});

						// Helper for number formatting
						var fmt_le = (n) => n.toLocaleString('en-US', {{maximumFractionDigits: 0}});
						var fmtPct_le = (n) => n.toLocaleString('en-US', {{minimumFractionDigits: 1, maximumFractionDigits: 1}});

						var targetData = data_component_learner_engagement.filter(d => {1} {2} d["simname"] == simSelector.value);
						var total = (targetData.length > 0) ? targetData[0]["total"] : 0;
						
						var t1 = document.getElementById("text_component_learner_engagement_1");

						if(total == 0){{
							t1.innerHTML = '<p class="component_text"><span style="font-weight:700">0</span> <span style="font-weight:400"> learners have engaged with the Simulation.</span></p>';
						}}
						else{{
							var singPlur = (total == 1) ? " learner has " : " learners have ";
							var html = '<p class="component_text">' +
									   '<span style="font-weight:700">' + fmt_le(total) + '</span>' +
									   '<span style="font-weight:400">' + singPlur + 'engaged with the Simulation.</span><br><br>';
							
							// Add breakdown text
							var stat1 = targetData.find(d => d["stat_order"] == 1);
							if (stat1 && stat1["n"] > 0) {{
								html += '<span style="font-weight:700">' + fmtPct_le(stat1["pct"]) + '% (' + fmt_le(stat1["n"]) + ')</span>' + 
										'<span style="font-weight:400"> of learners have not yet completed their first attempt.</span><br>';
							}}
							
							var stat2 = targetData.find(d => d["stat_order"] == 2);
							if (stat2) {{
								html += '<span style="font-weight:700">' + fmtPct_le(stat2["pct"]) + '% (' + fmt_le(stat2["n"]) + ')</span>' + 
										'<span style="font-weight:400"> of learners have completed an attempt.</span><br>';
							}}
							
							html += '</p>';
							t1.innerHTML = html;

							// --- Plotly Chart ---
							var plotDataRaw = targetData.filter(d => d["stat_order"] <= 2);
							var values = plotDataRaw.map(d => d["pct"]);
							var labels = plotDataRaw.map(d => d["stat"]);
							var colors = plotDataRaw.map(d => d["bar_color"]);

							var data = [{{
							  values: values,
							  labels: labels,
							  marker: {{colors: colors}},
							  type: 'pie',
							  hole: 0.6,
							  textinfo: 'percent',
							  textposition: 'outside',
							  hoverinfo: 'label+value+percent',
							  name: 'Learner Engagement'
							}}];

							var layout = {{
							  height: 400,
							  width: 500,
							  showlegend: false,
							  margin: {{t: 20, b: 20, l: 20, r: 20}},
							  annotations: [
								{{
								  font: {{
									size: 40,
									weight: 700,
                                family: body_font
								  }},
								  showarrow: false,
								  text: fmt_le(total),
								  x: 0.5,
								  y: 0.55
								}},
								{{
								  font: {{
									size: 14,
                                family: body_font
								  }},
								  showarrow: false,
								  text: "Learners",
								  x: 0.5,
								  y: 0.45
								}}
							  ]
							}};

							Plotly.newPlot('chart_component_learner_engagement_1', data, layout);

							// --- Second Text Grid Element ---
							var t2 = document.getElementById("text_component_learner_engagement_2");
							var html2 = '<p class="component_text">';
							
							var stat3 = targetData.find(d => d["stat_order"] == 3);
							if (!stat3 || stat3["n"] == 0) {{
								html2 += '<span style="font-weight:700">0</span> <span style="font-weight:400"> learners have completed multiple attempts.</span><br>';
							}} else {{
								html2 += '<span style="font-weight:700">' + fmtPct_le(stat3["pct"]) + '% (' + fmt_le(stat3["n"]) + ')</span>' +
										 '<span style="font-weight:400"> of learners have completed </span>' +
										 '<span style="font-weight:700">2 or more</span>' +
										 '<span style="font-weight:400"> attempts.</span><br>';
										 
								var stat4 = targetData.find(d => d["stat_order"] == 4);
								if (stat4) {{
									html2 += '<span style="font-weight:700">' + fmtPct_le(stat4["pct"]) + '% (' + fmt_le(stat4["n"]) + ')</span>' +
											 '<span style="font-weight:400"> of learners have completed </span>' +
											 '<span style="font-weight:700">3 or more</span>' +
											 '<span style="font-weight:400"> attempts.</span><br>';
								}}
								
								var stat5 = targetData.find(d => d["stat_order"] == 5);
								if (stat5) {{
									html2 += '<span style="font-weight:700">' + fmtPct_le(stat5["pct"]) + '% (' + fmt_le(stat5["n"]) + ')</span>' +
											 '<span style="font-weight:400"> of learners have completed </span>' +
											 '<span style="font-weight:400">4 or more</span>' +
											 '<span style="font-weight:400"> attempts.</span><br>';
								}}
							}}
							html2 += '</p>';
							t2.innerHTML = html2;

							chart_bar_vertical_character(
							  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] >= 3),
							  html_id="#chart_component_{0}_2",

							  x={{var:{{start:"stat", end:null}}, order:"as_appear", ascending:true}}, // Must be character
							  y={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric

							  title={{value:null, line:false}},

							  clr={{var:"bar_color", value:"#e32726"}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  bar={{
								size:14, weight:700,
								text:[
								  {{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
								  {{var:"n", format:",.0f", prefix:"(", suffix:")"}},
								],
								maxWidth:30
							  }},

							  tooltip_text=[
								{{size:14, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:" attempts completed"}}]}},
								{{size:14, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
								{{size:14, weight:400, text:[
								  {{var:"n", format:",.0f", prefix:null, suffix:null}},
								  {{var:"total", format:",.0f", prefix:" / ", suffix:null}}
								]}}
							  ],

							  barmode="overlay", // "group", "overlay" or "stack"

							  hline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								label:{{value:"Attempts Completed", size:14, weight:700}},
								offset:{{left:10, right:10}},
								tick:{{size:14, weight:400, orientation:"h", splitWidth:150}},
								show:true,
								show_line:false,
								show_ticks:false,
							  }},

							  yaxis={{
								height:350,
								label:{{value:"Percent of Learners", size:14, weight:700}},
								offset:{{top:10, bottom:10}},
								range:[0, 100],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:"%",
								format:null,
								tick:{{size:12, weight:400, width:150}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:6,
								show_grid:true
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:500}},

							  zoom=false
							);
						}}
					}} catch (e) {{
						console.error("Error in Learner Engagement Chart:", e);
					}}


					'''.format(key2, proj_selector, dmg_selector)





				if key2 == 'learner_engagement_over_time':
					html_page += '''
					// LEARNER ENGAGEMENT OVER TIME

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] == 0){{

					  // --- First Text Grid Element --->
					  d3.select("#text_component_{0}_1")
							.append("p")
							.attr("class", "component_text");

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}
					else{{

						var sing_plur_{0} = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] == 1)? " learner has ": " learners have ";

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 700)
								.text(d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0]))
							  .append("tspan")
								.style("font-weight", 400)
								.text(sing_plur_{0} + "completed an attempt.");


						var xaxis_freq = data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["time_freq"])[0];
						if(xaxis_freq == "d"){{
							var xaxis_freq = "Date"
						}}
						else if(xaxis_freq == "w"){{
							var xaxis_freq = "Week"
						}}
						else if(xaxis_freq == "m"){{
							var xaxis_freq = "Month"
						}}
						else if(xaxis_freq == "q"){{
							var xaxis_freq = "Quarter"
						}}
						else if(xaxis_freq == "y"){{
							var xaxis_freq = "Year"
						}}

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_vertical_character(
							data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["n_cum"] > 0),
							html_id="#chart_component_{0}_1",

							x={{var:{{start:"dt_char", end:null}}, order:"as_appear", ascending:true}}, // Must be character
							y={{var:"n", ascending:true, ci:[null, null]}}, // Must be numeric

							title={{value:null, line:false}},

							clr={{var:"bar_color", value:"#e32726"}}, // Variable containing color of bar(s) or value to set all bars to same color
							opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							group={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, show:true}},
							switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							bar_text={{
								size:14, weight:400,
								text:[{{var:"n", format:",.0f", prefix:null, suffix:null}}],
								maxWidth:30
							}},

							tooltip_text=[
							  {{size:16, weight:700, text:[{{var:"dt_char", format:null, prefix:null, suffix:null}}]}},
							  {{size:16, weight:700, text:[{{var:"n", format:",.0f", prefix:null, suffix:" Learners"}}]}},
							  {{size:14, weight:400, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
							],

							barmode="overlay", // "group", "overlay" or "stack"

							hline={{
							  var:null,
							  value:null
							}},

							xaxis={{
								label:{{value:xaxis_freq, size:14, weight:700}},
								offset:{{left:10, right:10}},
								tick:{{size:14, weight:400, orientation:"v", splitWidth:150}},
								show:true,
								show_line:false,
								show_ticks:false
							}},

							yaxis={{
								height:400,
								label:{{value:"Number of Learners", size:14, weight:700}},
								offset:{{top:10, bottom:10}},
								range:[0, null],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:null,
								format:",.0f",
								tick:{{size:12, weight:400, width:150}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:Math.min(7, (d3.max(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])))+1),
								show_grid:true
							}},

							font={{family:body_font}},

							margin={{top:10, bottom:10, left:10, right:10, g:10}},

							canvas={{width:1000}},

							zoom=false
						  );
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'overall_pass_rates':
					html_page += '''
					// OVERALL PASS RATES

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n_skills"])[0] == 0){{

						// --- First Text Grid Element --->
						d3.select("#text_component_{0}_1")
							  .append("p")
							  .attr("class", "component_text");

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("Simulation has no Pass/Fail settings.");

					}}

					else if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] == 0){{

					  // --- First Text Grid Element --->
					  d3.select("#text_component_{0}_1")
							.append("p")
							.attr("class", "component_text");

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}

					else{{

						chart_donut(
							data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
							html_id="#chart_component_{0}_1",

							title={{value:null, line:false}},

							clr={{var:"bar_color", value:null}},

							facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							group={{var:"stat", label:{{value:"Attempts needed to Pass:", size:16, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
							switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							value={{
							  var:"pct",
							  max:100,
							  maxScroll:"fixed", // "fixed" or "free"
							  maxFacet:"fixed", // "fixed" or "free"
							}},

							segment_label={{
							  minValue:0.02,
							  text:[
								{{size:14, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:" Attempt(s)"}}]}},
								{{size:14, weight:400, text:[
									{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
									{{var:"n", format:",.0f", prefix:" (", suffix:")"}},
								]}}
							  ]
							}},

							tooltip_text=[
							  {{size:16, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:" Attempts(s)"}}]}},
							  {{size:16, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
							  {{size:14, weight:400, text:[
								{{var:"n", format:",.0f", prefix:null, suffix:null}},
								{{var:"total", format:",.0f", prefix:" / ", suffix:null}}
							  ]}}
							],

							inner_circle={{
							  clr:"#d3d2d2",
							  width:0.5, // Value between 0 and 1 representing the percentage width of the outer circle
							  show:true
							}},

							inner_radius=0.8,

							inner_text=[
							  {{size:50, weight:700, text:[
								{{var:"pct", aggregate:"sum", format:",.1f", prefix:null, suffix:"%"}},
							  ]}},
							  {{size:18, weight:700, text:[{{var:null, aggregate:null, format:null, prefix:"of Learners Passed", suffix:null}}]}},
							  {{size:18, weight:400, text:[
								{{var:"n", aggregate:"sum", format:",.0f", prefix:"(", suffix:null}},
								{{var:"total", aggregate:"max", format:",.0f", prefix:" / ", suffix:")"}},
							  ]}}
							],

							yaxis={{
							  height:400,
							  offset:{{top:10, bottom:10}},
							  tick:{{width:100}}
							}},

							font={{family:body_font}},

							margin={{top:10, bottom:10, left:10, right:10, g:10}},

							canvas={{width:1000}},

							zoom=false
						);
					}}


					'''.format(key2, proj_selector, dmg_selector)





				if key2 == 'skill_pass_rates':
					html_page += '''
					// SKILL PASS RATES

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n_skills"])[0] == 0){{

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("Simulation does not have a Pass/Fail setting on any Skill.");

					}}
					else{{
						var sing_plur_{0} = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] == 1)? " learner has ": " learners have ";

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 700)
								.text(d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0]))
							  .append("tspan")
								.style("font-weight", 400)
								.text(sing_plur_{0} + "completed an attempt.");


						if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] > 0){{

							Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["skillname"]))).forEach((v, i) => {{

								if(i == 0){{
									d3.select("#text_component_{0}_1").select(".component_text").append("br");
								}}

								d3.select("#text_component_{0}_1").select(".component_text").append("br");

								d3.select("#text_component_{0}_1").select(".component_text")
								  .append("text")
								  .attr("dx", "0em")
								  .attr("dy", "0em")
									.append("tspan")
									  .style("font-weight", 700)
									  .text(numFormat(d3.sum(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["skillname"] == v).map(d => d["pct"]))) + "% ")
									.append("tspan")
									  .style("font-weight", 700)
									  .text("(" + d3.format(",.0f")(d3.sum(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["skillname"] == v).map(d => d["n"]))) + ") ")
									.append("tspan")
									  .style("font-weight", 400)
									  .text(" of learners have passed ")
									.append("tspan")
									  .style("font-weight", 700)
									  .text(v)
									.append("tspan")
									  .style("font-weight", 400)
									  .text(" in an attempt.");
							}})



							// --- Chart Grid Element --->
							chart_bar_horizontal(
								data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
								html_id="#chart_component_{0}_1",

								x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
								y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

								title={{value:null, line:false}},

								clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
								opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

								facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
								group={{var:"stat", label:{{value:"Attempts needed to Pass:", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
								switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
								scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

								bar={{
								  size:14, weight:400,
								  text:[
									  {{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
								  ],
								  extra_height:0,
								  space_between:10
								}},

								tooltip_text=[
								  {{size:14, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[
									  {{var:"stat", format:null, prefix:null, suffix:null}},
									  {{var:"stat_suffix", format:null, prefix:" ", suffix:":"}},
								  ]}},
								  {{size:14, weight:700, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								  {{size:14, weight:400, text:[
									  {{var:"n", format:",.0f", prefix:"(", suffix:null}},
									  {{var:"total", format:",.0f", prefix:" out of ", suffix:" Learners)"}},
									  ]
								  }},
								],

								barmode="stack", // "group", "stack" or "overlay"

								column_data = {{
								  before_x:null,
								  after_x:{{var:"total_pct", format:",.1f", prefix:null, suffix:"%", size:14, weight:700, color:{{var:null, value:"#339933"}}, label:{{value:"Total Pass Rate", size:12, weight:700, padding:{{top:10, bottom:0}}}}}}
								}},

								vline={{
								  var:null,
								  value:null
								}},

								xaxis={{
								  range:[0, 100],
								  rangeScroll:"fixed", // "fixed" or "free"
								  rangeFacet:"fixed", // "fixed" or "free"
								  format:",.0f",
								  suffix:"%",
								  tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
								  label:{{value:"Percent of Learners", size:14, weight:700}},
								  offset:{{left:10, right:10}},
								  show:true,
								  show_line:false,
								  show_ticks:true,
								  num_ticks:6,
								  show_grid:true
								}},

								yaxis={{
								  widthPct:{{value:0.4, range:"free"}},
								  rangeScroll:"fixed", // "fixed" or "free"
								  rangeFacet:"fixed", // "fixed" or "free"
								  tick:{{size:14, weight:700}},
								  label:{{value:"Skill", size:14, weight:700}},
								  offset:{{top:0, bottom:10}},
								  show:true,
								  show_line:false,
								  show_ticks:false,
								}},

								font={{family:body_font}},

								margin={{top:10, bottom:10, left:10, right:10, g:10}},

								canvas={{width:1000}},

								zoom=false
							);
						 }}
					}}


					'''.format(key2, proj_selector, dmg_selector)





				if key2 == 'skill_baseline':
					html_page += '''
					// SKILL SCORES - BASELINE

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("Simulation has no Skills.");

					}}
					else if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0] == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}
					else{{

						var sing_plur_ovl_{0} = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0] == 1)? " learner has ": " learners have ";

						d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text(d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0]))
							.append("tspan")
							  .style("font-weight", 400)
							  .text(sing_plur_ovl_{0} + " completed their first attempt.");


						var vline_label = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["bench"] != null).length > 0)? "Pass Setting": null;

						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"avg_skillscore", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:14, weight:400,
							text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}],
							extra_height:0,
							space_between:14
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}]}},
							{{size:14, weight:400, text:[{{var:"n", format:",.0f", prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  barmode="group", // "group", "stack" or "overlay"

						  column_data = {{
							before_x:null,
							after_x:null
						  }},

						  vline={{
							var:{{name:"bench", line_style:"dashed", clr:"red", width:1.5, label:vline_label }},
							value:null
						  }},

						  xaxis={{
							range: [0, 100],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix: "%",
							tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
							label:{{value:"Average Performance", size:14, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:6,
							show_grid:true
						  }},

						  yaxis={{
							widthPct:{{value:0.4, range:"free"}},
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:14, weight:700}},
							label:{{value:"Skill", size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'skill_improvement':
					html_page += '''
					// SKILL SCORES - IMPROVEMENT

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("Simulation has no Skills.");

					}}
					else if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0] == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed multiple attempts.");

					}}
					else{{

						var sing_plur_ovl_{0} = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0] == 1)? " learner has ": " learners have ";

						d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text(d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0]))
							.append("tspan")
							  .style("font-weight", 400)
							  .text(sing_plur_ovl_{0} + " completed multiple attempts.");


						var vline_label = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["bench"] != null).length > 0)? "Pass Setting": null;

						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"avg_skillscore", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
						  group={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:12, weight:400,
							text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}],
							extra_height:0,
							space_between:14
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:10, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}]}},
							{{size:14, weight:400, text:[{{var:"n", format:",.0f", prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  barmode='group', // 'group' or 'stack'

						  column_data={{
							before_x:null,
							after_x:{{var:"avg_chg_skillscore", format:'+.1f', prefix:null, suffix:"%", size:14, weight:700, color:{{var:null, value:"#339933"}}, label:{{value:"Average Performance Improvement", size:12, weight:700, padding:{{top:0, bottom:0}}}}}}
						  }},

						  vline={{
							var:{{name:"bench", line_style:"dashed", clr:"red", width:1.5, label:vline_label }},
							value:null
						  }},

						  xaxis={{
							range:[0, 100],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix:"%",
							tick:{{size:10, weight:400, orientation:'h', splitWidth:150}},
							label:{{value:"Average Performance", size:14, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:6,
							show_grid:true
						  }},

						  yaxis={{
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:14, weight:700}},
							label:{{value:"Skill", size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'decision_levels':
					html_page += '''
					// DECISION LEVEL SUMMARY

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total_sim"])[0] == 0){{

					  // --- First Text Grid Element --->
					  d3.select("#text_component_{0}_1")
							.append("p")
							.attr("class", "component_text");

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}
					else{{

						if( Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["coaching"]))).some(element => element != "-") ){{
							  var tooltipText = [
								  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
								  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:null, format:null, prefix:"Coaching:", suffix:null}}]}},
								  {{size:13, weight:400, text:[{{var:"coaching", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								  {{size:12, weight:400, text:[
									{{var:"n", format:",.0f", prefix:"(", suffix:" out of "}},
									{{var:"total_decision", format:",.0f", prefix:null, suffix:" Learners)"}},
								  ]}}
							  ];
						}}
						else if( Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["feedback"]))).some(element => element != "-") ){{
							  var tooltipText = [
								  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
								  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:null, format:null, prefix:"Feedback:", suffix:null}}]}},
								  {{size:13, weight:400, text:[{{var:"feedback", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								  {{size:12, weight:400, text:[
									{{var:"n", format:",.0f", prefix:"(", suffix:" out of "}},
									{{var:"total_decision", format:",.0f", prefix:null, suffix:" Learners)"}},
								  ]}}
							  ];
						}}
						else{{
							  var tooltipText = [
								  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
								  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
								  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
								  {{size:14, weight:700, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								  {{size:12, weight:400, text:[
									{{var:"n", format:",.0f", prefix:"(", suffix:" out of "}},
									{{var:"total_decision", format:",.0f", prefix:null, suffix:" Learners)"}},
								  ]}}
							  ];
						}}

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
							data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
							html_id="#chart_component_{0}_1",

							x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
							y={{var:"scenario", order:"as_appear", ascending:true, highlight:{{var:"skills", title:"SELECT SKILL:"}} }}, // Must be categorical

							title={{value:null, line:false}},

							clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
							opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							facet={{var:"section", size:16, weight:700, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
							group={{var:"decisiontype", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"decision_ord", ascending:true, show:true}},
							switcher={{var:"attempt_n", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
							scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							bar={{
							  size:14, weight:400,
							  text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}],
							  extra_height:6,
							  space_between:5,
							  var:'rect_height'
							}},

							tooltip_text=tooltipText,

							barmode="stack", // "group", "overlay" or "stack"

							column_data={{
							  before_x:null,
							  after_x:null
							}},

							vline={{
							  var:null,
							  value:null
							}},

							xaxis={{
							  range:[0, 100],
							  rangeScroll:"fixed", // "fixed" or "free"
							  rangeFacet:"fixed", // "fixed" or "free"
							  format:",.0f",
							  suffix:"%",
							  tick:{{size:10, weight:400, orientation:'h', splitWidth:150}},
							  label:{{value:null, size:14, weight:700}},
							  offset:{{left:10, right:10}},
							  show:false,
							  show_line:false,
							  show_ticks:true,
							  num_ticks:6,
							  show_grid:true
							}},

							yaxis={{
							  widthPct:{{value:0.4, range:'free', cutText:true}},
							  rangeScroll:"fixed", // "fixed" or "free"
							  rangeFacet:"free", // "fixed" or "free"
							  tick:{{size:14, weight:400}},
							  label:{{value:"Decision Level", size:14, weight:700}},
							  offset:{{top:0, bottom:10}},
							  show:true,
							  show_line:false,
							  show_ticks:false,
							}},

							font={{family:body_font}},

							margin={{top:10, bottom:10, left:10, right:10, g:10}},

							canvas={{width:1000}},

							zoom=false
						  );
					}}


					'''.format(key2, proj_selector, dmg_selector)





				if key2 == 'behaviors':
					html_page += '''
					// LEARNER BEHAVIORS AND DECISIONS

					d3.select("#contentsub_{0}").remove();


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

						// --- 1x1 Grid --->
						d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
						  .append("div")
						  .attr("id", "contentsub_{0}")
						  .style("display", "grid")
						  .style("grid-template-rows", "min-content")
						  .style("grid-template-columns", "1fr")
						  .style("grid-gap", "5px");

					  d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");


					  // --- First Text Grid Element --->
					  d3.select("#text_component_{0}_1")
							.append("p")
							.attr("class", "component_text");

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("Simulation has no Behaviors.");

					}}
					else{{

						// --- Nx1 Grid --->
						var num_graphs_{0} = Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["behaviorid"]))).length;

						d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
						  .append("div")
						  .attr("id", "contentsub_{0}")
						  .style("display", "grid")
						  .style("grid-template-rows", "min-content ".repeat(num_graphs_{0}))
						  .style("grid-template-columns", "1fr")
						  .style("grid-gap", "5px");

						for(i=1; i<=num_graphs_{0}; i++){{
							d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_" + i).style("align-self", "start");
						}}


						var behaviors_{0} = data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).filter((thing, index, self) =>
						  index === self.findIndex((t) => (
							t["typeid"] === thing["typeid"] && t["behaviorid"] === thing["behaviorid"] && t["behavior"] === thing["behavior"]
						  ))
						);

						behaviors_{0}.forEach((vBehavior, iBehavior) => {{

							chart_bar_horizontal(
								data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["behaviorid"] == vBehavior["behaviorid"]),
								html_id="#chart_component_{0}_" + (iBehavior+1),

								x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
								y={{var:"consequence", order:"as_appear", ascending:true}}, // Must be categorical

								title={{value:[
									{{size:17, weight:700, text:vBehavior["behavior"]}},
									//{{size:17, weight:700, text:"(" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["behaviorid"] == vBehavior["behaviorid"]).map(d => d["total"])[0]) + " Learners)"}},
								], line:false}},

								clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
								opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

								facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
								group={{var:"decisiontype", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
								switcher={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"alphabetical", ascending:true, line:false}},
								scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

								bar={{
								  size:14, weight:400,
								  text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}],
								  extra_height:0,
								  space_between:10
								}},

								tooltip_text=[
								  {{size:16, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:null}}]}},
								  {{size:16, weight:400, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
								  {{size:14, weight:400, text:[
									{{var:"n", format:",.0f", prefix:null, suffix:null}},
									{{var:"total", format:",.0f", prefix:" / ", suffix:null}}
								  ]}}
								],

								barmode="overlay", // "group" or "stack"

								column_data = {{
								  before_x:null,
								  after_x:null
								}},

								vline={{var:null, value:null}},

								xaxis={{
								  range: [0, 100],
								  rangeScroll:"fixed", // "fixed" or "free"
								  rangeFacet:"fixed", // "fixed" or "free"
								  suffix: "%",
								  tick:{{size:10, weight:400}},
								  label:{{value:"Percent of Learners", size:14, weight:700}},
								  offset: {{left:10, right:10}},
								  show:true,
								  show_line:false,
								  show_ticks:true,
								  num_ticks:6,
								  show_grid:true
								}},

								yaxis={{
								  widthPct:{{value:0.49, range:"fixed"}},
								  rangeScroll:"fixed", // "fixed" or "free"
								  rangeFacet:"fixed", // "fixed" or "free"
								  tick:{{size:14, weight:400}},
								  label:{{value:null, size:20, weight:700}},
								  offset: {{top:10, bottom:10}},
								  show:true,
								  show_line:false,
								  show_ticks:false,
								}},

								font={{family:body_font}},

								margin={{top:10, bottom:10, left:10, right:10, g:10}},

								canvas={{width:1000}},

								zoom=false
							);

						}});

					}}


					'''.format(key2, proj_selector, dmg_selector)





				if key2 == 'time_spent':
					html_page += '''
					// TIME SPENT IN TASK MODE

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							 .append("tspan")
								.style("font-weight", 700)
								.text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}
					else{{

						var stat_order_value_{0} = (data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length > 2)? 5: 1;

						chart_bar_vertical_character(
							data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] <= stat_order_value_{0}),
							html_id="#chart_component_{0}_1",

							x={{var:{{start:"stat", end:null}}, order:"as_appear", ascending:true}}, // Must be character
							y={{var:"avg_cum_duration", ascending:true, ci:[null, null]}}, // Must be numeric

							title={{value:null, line:false}},

							clr={{var:"bar_color", value:"#e32726"}}, // Variable containing color of bar(s) or value to set all bars to same color
							opacity={{var:"opac", value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							group={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true}},
							switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							bar_text={{
								size:14, weight:400,
								text:[{{var:"avg_cum_duration", format:",.1f", prefix:null, suffix:null}}],
								  maxWidth:30
							}},

							tooltip_text=[
							  {{size:16, weight:700, text:[{{var:null, format:null, prefix:"Average time to complete", suffix:null}}]}},
							  {{size:16, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:":"}}]}},
							  {{size:16, weight:400, text:[{{var:"avg_cum_duration", format:",.1f", prefix:null, suffix:" minutes"}}]}}
							],

							barmode="overlay", // "group", "overlay" or "stack"

							hline={{
							  var:null,
							  value:null
							}},

							xaxis={{
								label:{{value:null, size:14, weight:700}},
								offset: {{left:10, right:10}},
								tick:{{size:14, weight:400, orientation:"h", splitWidth:150}},
								show:true,
								show_line:false,
								show_ticks:false
							}},

							yaxis={{
								height:400,
								label:{{value:"Time to Complete Attempts (mins)", size:14, weight:700}},
								offset: {{top:10, bottom:10}},
								range:[0, Math.ceil(d3.max(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] <= stat_order_value_{0}).map(d => d["avg_cum_duration"]))/ 60)*60 ],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:null,
								format:",.0f",
								tick:{{size:12, weight:400, width:150}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:7,
								show_grid:true
							}},

							font={{family:body_font}},

							margin={{top:10, bottom:10, left:10, right:10, g:10}},

							canvas={{width:1000}},

							zoom=false
						  );
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'practice_mode':
					html_page += '''
					// PRACTICE MODE

					d3.select("#contentsub_{0}").remove();

					// --- 2x2 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr 1fr")
					  .style("grid-gap", "5px")
					  .style("margin-bottom", "20px");

					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "text_component_{0}_2").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "chart_component_{0}_1").style("align-self", "start");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "chart_component_{0}_2").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
					d3.select("#chart_component_{0}_2").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["total"])[0] == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							 .append("tspan")
								.style("font-weight", 700)
								.text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt.");

					}}
					else{{

						// --- First Chart Grid Element --->
						chart_donut(
						  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
						  html_id="#chart_component_{0}_1",

						  title={{value:null, line:false}},

						  clr={{var:null, value:"#339933"}},

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:null, label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:false}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  value={{
							var:"pct",
							max:100,
							maxScroll:"fixed", // "fixed" or "free"
							maxFacet:"fixed", // "fixed" or "free"
						  }},

						  segment_label={{
							minValue:0.00,
							text:null
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
							{{size:14, weight:400, text:[
							  {{var:"n", format:",.0f", prefix:null, suffix:null}},
							  {{var:"total", format:",.0f", prefix:" / ", suffix:null}}
							]}}
						  ],

						  inner_circle={{
							clr:"#d3d2d2",
							width:0.5, // Value between 0 and 1 representing the percentage width of the outer circle
							show:true
						  }},

						  inner_radius=0.8,

						  inner_text=[
							  {{size:40, weight:700, text:[
								{{var:"pct", aggregate:"max", format:",.1f", prefix:null, suffix:"%"}},
							  ]}},
							  {{size:16, weight:700, text:[{{var:null, aggregate:null, format:null, prefix:"of Learners accessed", suffix:null}}]}},
							  {{size:16, weight:700, text:[{{var:null, aggregate:null, format:null, prefix:"Practice Mode", suffix:null}}]}},
							  {{size:14, weight:400, text:[
								{{var:"n", aggregate:"max", format:",.0f", prefix:"(", suffix:null}},
								{{var:"total", aggregate:"max", format:",.0f", prefix:" / ", suffix:")"}},
							  ]}}
							],

						  yaxis={{
							height:350,
							offset:{{top:10, bottom:10}},
							tick:{{width:0}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:500}},

						  zoom=false
						);


						if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["n"])[0] > 0){{

							// --- Second Chart Grid Element --->
							chart_bar_vertical_character(
							  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value),
							  html_id="#chart_component_{0}_2",

							  x={{var:{{start:"simname", end:null}}, order:"as_appear", ascending:true}}, // Must be character
							  y={{var:"avg_practice_duration", ascending:true, ci:[null, null]}}, // Must be numeric

							  title={{value:null, line:false}},

							  clr={{var:null, value:"#1f77b4"}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  bar={{
								size:14, weight:700,
								text:[
								  {{var:"avg_practice_duration", format:",.1f", prefix:null, suffix:null}}
								],
								maxWidth:30
							  }},

							  tooltip_text=[
								{{size:14, weight:700, text:[{{var:null, format:null, prefix:"Average time spent", suffix:null}}]}},
								{{size:14, weight:700, text:[{{var:null, format:null, prefix:"in Practice Mode:", suffix:null}}]}},
								{{size:14, weight:400, text:[{{var:"avg_practice_duration", format:".1f", prefix:null, suffix:" minutes"}}]}},
								{{size:14, weight:400, text:[
								  {{var:"n", format:",.0f", prefix:"(", suffix:" Learners)"}}
								]}}
							  ],

							  barmode="overlay", // "group", "overlay" or "stack"

							  hline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								label:{{value:null, size:14, weight:700}},
								offset: {{left:10, right:10}},
								tick:{{size:14, weight:400, orientation:"h", splitWidth:150}},
								show:false,
								show_line:false,
								show_ticks:false,
							  }},

							  yaxis={{
								height:350,
								label:{{value:"Time Spent in Practice Mode (mins)", size:14, weight:700}},
								offset: {{top:10, bottom:10}},
								range:[0, Math.ceil(d3.max(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["avg_practice_duration"]))/ 60)*60 ],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:null,
								format:",.0f",
								tick:{{size:12, weight:400, width:150}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:7,
								show_grid:true
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:500}},

							  zoom=false
							);

						}}
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'knowledge_check_1':
					html_page += '''
					// KNOWLEDGE CHECK

					d3.select("#contentsub_knowledge_check").remove();

					if(data_component_knowledge_check_1.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

						// --- 1x1 Grid --->
						d3.select("#component_content_knowledge_check_1")
						  .append("div")
						  .attr("id", "contentsub_knowledge_check")
						  .style("display", "grid")
						  .style("grid-template-rows", "min-content")
						  .style("grid-template-columns", "1fr")
						  .style("grid-gap", "5px");

						d3.select("#contentsub_knowledge_check").append("div").attr("id", "text_component_knowledge_check_1").style("align-self", "end");


						// --- First Text Grid Element --->
						d3.select("#text_component_knowledge_check_1")
							  .append("p")
							  .attr("class", "component_text");

						d3.select("#text_component_knowledge_check_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("Simulation has no Knowledge Checks.");
					}}
					else{{


						var knowledge_questions = data_component_knowledge_check_1.filter(d => {1} {2} d["simname"] == simSelector.value).filter((thing, index, self) =>
							index === self.findIndex((t) => (
							  t["typeid"] === thing["typeid"] && t["orderid"] === thing["orderid"] && t["question"] === thing["question"]
							))
						);

						knowledge_questions.forEach((vQuestion, iQuestion) => {{

								// --- 1x1 Grid --->
								d3.select("#component_content_knowledge_check_1")
								  .append("div")
								  .attr("id", "contentsub_knowledge_check_" + iQuestion + "_title")
								  .style("display", "grid")
								  .style("grid-template-rows", "min-content")
								  .style("grid-template-columns", "1fr")
								  .style("grid-gap", "5px");

								d3.select("#contentsub_knowledge_check_" + iQuestion + "_title").append("div").attr("id", "text_component_knowledge_check_" + iQuestion).style("align-self", "end");


								// --- 1x2 Grid --->
								d3.select("#component_content_knowledge_check_1")
								  .append("div")
								  .attr("id", "contentsub_knowledge_check_" + iQuestion)
								  .attr("class", "grid")
								  .style("display", "grid")
								  .style("grid-template-rows", "min-content")
								  .style("grid-template-columns", "1fr 1fr")
								  .style("grid-gap", "5px")
								  .style("margin-bottom", "30px");

								d3.select("#contentsub_knowledge_check_" + iQuestion ).append("div").attr("class", "grid__item").attr("id", "chart_component_knowledge_check_" + iQuestion + "_1").style("align-self", "start");
								d3.select("#contentsub_knowledge_check_" + iQuestion ).append("div").attr("class", "grid__item").attr("id", "chart_component_knowledge_check_" + iQuestion + "_2").style("align-self", "start");

								d3.select("#text_component_knowledge_check_" + iQuestion).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text(vQuestion["question"]);
								d3.select("#text_component_knowledge_check_" + iQuestion).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text("(" + d3.format(",")(data_component_knowledge_check.filter(d => {1} {2} d["simname"] == simSelector.value && d["question"] == vQuestion["question"]).map(d => d["total"])[0]) + " Responses)");


								// --- First Chart Grid Element --->

								chart_bar_horizontal(
								  data=data_component_knowledge_check_1.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]),
								  html_id="#chart_component_knowledge_check_" + iQuestion + "_1",

								  x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
								  y={{var:"answer", order:"as_appear", ascending:true}}, // Must be categorical

								  title={{value:[
									{{size:16, weight:700, text: "First Selected Response"}}
								  ], line:false}},

								  clr={{var:"bar_color", value:"#e32726"}}, // Variable containing color of bar(s) or value to set all bars to same color
								  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

								  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
								  group={{var:"answer_type", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"alphabetical", ascending:true, show:true}},
								  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
								  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

								  bar={{
									size:14, weight:400,
									text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}],
									extra_height:0,
									space_between:5
								  }},

								  tooltip_text=[
									{{size:16, weight:700, text:[{{var:"answer_type", format:null, prefix:null, suffix:null}}]}},
									  {{size:16, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
									  {{size:14, weight:400, text:[
										{{var:"n", format:",.0f", prefix:null, suffix:null}},
										{{var:"total", format:",.0f", prefix:" / ", suffix:null}}
									  ]}}
								  ],

								  barmode="overlay", // "group", "stack" or "overlay"

								  column_data={{before_x:null, after_x:null}},

								  vline={{var:null, value:null}},

								  xaxis={{
									range: [0, 100],
									rangeScroll:"fixed", // "fixed" or "free"
									rangeFacet:"fixed", // "fixed" or "free"
									suffix:"%",
									tick:{{size:10, weight:400}},
									label:{{value:"Percent of Learners", size:14, weight:700}},
									offset: {{left:10, right:10}},
									show:true,
									show_line:false,
									show_ticks:true,
									num_ticks:5,
									show_grid:true
								  }},

								  yaxis={{
									widthPct:{{value:0.4, range:"free"}},
									rangeScroll:"fixed", // "fixed" or "free"
									rangeFacet:"fixed", // "fixed" or "free"
									tick:{{size:14, weight:400}},
									label:{{value:null, size:14, weight:700}},
									offset: {{top:10, bottom:10}},
									show:true,
									show_line:false,
									show_ticks:false,
								  }},

								  font={{family:body_font}},

								  margin={{top:10, bottom:10, left:10, right:10, g:10}},

								  canvas={{width:500}},

								  zoom=false
							  );




							  /*
							  // --- Second Chart Grid Element --->
							  chart_donut(
								data=data_component_knowledge_check_2.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]),
								html_id="#chart_component_knowledge_check_" + iQuestion + "_2",

								title={{value:[
								  {{size:16, weight:700, text: "Number of tries needed to get Correct Response"}}
								], line:false}},

								clr={{var:"bar_color", value:null}},

								facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
								group={{var:"attempts_needed", label:{{value:"Attempts needed:", size:16, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:false}},
								switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
								scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

								value={{
								  var:"pct",
								  max:100,
								  maxScroll:"fixed", // "fixed" or "free"
								  maxFacet:"fixed", // "fixed" or "free"
								}},

								segment_label={{
								  minValue:0.02,
								  text:[
									{{size:14, weight:700, text:[{{var:"attempts_needed", format:null, prefix:null, suffix:null}}]}},
									{{size:14, weight:400, text:[
									  {{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
									  {{var:"n", format:",.0f", prefix:" (", suffix:")"}},
									]}}
								  ]
								}},

								tooltip_text=[
									{{size:16, weight:700, text:[{{var:"attempts_needed", format:null, prefix:null, suffix:null}}]}},
									{{size:16, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
									{{size:14, weight:400, text:[
									  {{var:"n", format:",.0f", prefix:null, suffix:null}},
									  {{var:"total", format:",.0f", prefix:" / ", suffix:null}}
									]}}
								 ],

								inner_circle={{
								  clr:"#d3d2d2",
								  width:0.5, // Value between 0 and 1 representing the percentage width of the outer circle
								  show:true
								}},

								inner_radius=0.8,

								inner_text=null,

								yaxis={{
									height:400,
									offset:{{top:0, bottom:10}},
									tick:{{width:100}}
								}},

								font={{family:body_font}},

								margin={{top:10, bottom:0, left:10, right:10, g:0}},

								canvas={{width:500}},

								zoom=false
							  );
							  */

						}});
					}}


					'''.format(key2, proj_selector, dmg_selector)



				if key2 == 'survey_responses':

					srv_comment_limit = survey_comment_limit if survey_comment_limit is not None else "Infinity"

					html_page += '''
					// SURVEY RESPONSES

					d3.select("#contentsub_{0}").remove();

					if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).length == 0){{

						// --- 1x1 Grid --->
						d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
						  .append("div")
						  .attr("id", "contentsub_{0}")
						  .style("display", "grid")
						  .style("grid-template-rows", "min-content")
						  .style("grid-template-columns", "1fr")
						  .style("grid-gap", "5px");

						d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");


						// --- First Text Grid Element --->
						d3.select("#text_component_{0}_1")
							  .append("p")
							  .attr("class", "component_text");

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("Simulation has no Survey.");
					}}
					else{{

						// --- Nx1 Grid --->
						var num_graphs = Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).map(d => d["orderid"]))).length;

						d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
						  .append("div")
						  .attr("id", "contentsub_{0}")
						  .style("display", "grid")
						  .style("grid-template-rows", "min-content ".repeat(num_graphs))
						  .style("grid-template-columns", "1fr")
						  .style("grid-gap", "5px");

						for(i=1; i<=num_graphs; i++){{
							d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_" + i).style("align-self", "start");
						}}


						var survey_questions_{0} = data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value).filter((thing, index, self) =>
						  index === self.findIndex((t) => (
							t["typeid"] === thing["typeid"] && t["orderid"] === thing["orderid"] && t["question"] === thing["question"]
						  ))
						);

						survey_questions_{0}.forEach((vQuestion, iQuestion) => {{

							// NPS Score
							if(vQuestion["question"].includes("NPS")){{
								chart_donut(
									data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]),
									html_id="#chart_component_{0}_" + (iQuestion+1),

									title={{value:null, line:false}},

									clr={{var:"bar_color", palette:null, value:null}}, // Variable containing color of bar(s) or value to set all bars to same color

									facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
									group={{var:"answer", label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"alphabetical", ascending:false, show:false}},
									switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
									scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

									value={{
										var:"pct", // name of the variable that contains the values for the circle bars
										max:100,
										maxScroll:"fixed", // "fixed" or "free"
										maxFacet:"fixed", // "fixed" or "free"
									}},

									segment_label={{
										minValue:0.05, // value between 0 and 1 representing the minimum percentage of the circle that a segment must reach before a segment label is shown
										text:[
											{{size:14, weight:700, text:[{{var:"answer", format:null, prefix:null, suffix:null}}]}},
											{{size:14, weight:400, text:[
												{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
											]}},
											{{size:12, weight:400, text:[
												{{var:"n", format:",.0f", prefix:" (", suffix:" Learners)"}},
											]}},
										]
									}},

									tooltip_text=[
										{{size:18, weight:700, text:[{{var:"answer", format:null, prefix:null, suffix:null}}]}},
										{{size:16, weight:400, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
										{{size:14, weight:400, text:[
											{{var:"n", format:",.0f", prefix:null, suffix:null}},
											{{var:"total", format:",.0f", prefix:" / ", suffix:" Learners"}}
										]}}
									],

									inner_circle={{
										clr:"#d3d2d2",
										width:0.5, // Value between 0 and 1 representing the percentage width of the outer circle
										show:true
									}},

									inner_radius=0.8, // Value between 0 and 1. The higher the value, the thinner the donut

									inner_text=[
										{{size:22, weight:700, text:[{{var:null, aggregate:null, format:null, prefix:"NPS Score:", suffix:null}}]}},
										{{size:36, weight:700, text:[
											{{var:"avg_nps_score", aggregate:"max", format:"+,.2f", prefix:null, suffix:null}},
										]}},
										{{size:14, weight:400, text:[
											{{var:"total", aggregate:"max", format:",.0f", prefix:"(", suffix:" Learners)"}},
										]}},
									],

									yaxis={{
										height:350,
										offset:{{top:10, bottom:10}},
										tick:{{width:250}}
									}},

									font={{family:body_font}},

									margin={{top:10, bottom:10, left:10, right:10, g:10}},

									canvas={{width:1000}},

									zoom=false
								);

							}}

							// Free-text Questions
							else if(vQuestion["typeid"] == 4){{

								// Topic Analysis questions
								if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => d["topic_analysis"])[0] == 1){{

									var data = getDistinctRows(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]), ["simid", "simname", "orderid", "question", "total", "answerid", "topic_keywords", "n", "bar_color", "pct"]);
									var total_responses = data.map(d => d["total"])[0];

									d3.select("#chart_component_{0}_" + (iQuestion+1)).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text(vQuestion["question"]);
									d3.select("#chart_component_{0}_" + (iQuestion+1)).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text("(" + d3.format(",.0f")(total_responses) + " Responses)");


									//d3.select("#chart_component_{0}_" + (iQuestion+1)).selectAll('.svg-container').remove();
									chart_bar_horizontal(
										data=data,
										html_id="#chart_component_{0}_" + (iQuestion+1),

										x={{var:"n", ascending:true, ci:[null, null]}}, // Must be numeric
										y={{var:"topic_keywords", order:"as_appear", ascending:true, highlight:{{var:null, title:null}} }}, // Must be categorical

										title={{value:[{{size:14, weight:700, text:"Topic Analysis Summary"}}], line:false}},

										clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
										opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

										facet={{var:null, size:16, weight:700, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
										group={{var:null, label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"decision_ord", ascending:true, show:true}},
										switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
										scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

										bar={{
										  size:14, weight:400,
										  text:[{{var:"n", format:",.0f", prefix:null, suffix:null}}],
										  extra_height:6,
										  space_between:5,
										  var:null
										}},

										tooltip_text=[
											{{size:16, weight:700, text:[{{var:null, format:null, prefix:"Topic Keywords:", suffix:null}}]}},
											{{size:16, weight:400, text:[{{var:"topic_keywords", format:null, prefix:null, suffix:null}}]}},
											{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
											{{size:14, weight:700, text:[
											  {{var:"n", format:",.0f", prefix:null, suffix:null}},
											  {{var:"total", format:",.0f", prefix:" out of ", suffix:" Responses"}},
											  {{var:"pct", format:",.1f", prefix:" (", suffix:"%)"}}
											]}}
										],

										barmode="group", // "group", "overlay" or "stack"

										column_data={{
										  before_x:null,
										  after_x:null
										}},

										vline={{
										  var:null,
										  value:null
										}},

										xaxis={{
										  range:[0, total_responses],
										  rangeScroll:"fixed", // "fixed" or "free"
										  rangeFacet:"fixed", // "fixed" or "free"
										  format:",.0f",
										  suffix:null,
										  tick:{{size:10, weight:400, orientation:'h', splitWidth:150}},
										  label:{{value:"Number of Responses", size:14, weight:700}},
										  offset:{{left:10, right:10}},
										  show:true,
										  show_line:false,
										  show_ticks:true,
										  num_ticks:6,
										  show_grid:true
										}},

										yaxis={{
										  widthPct:{{value:0.4, range:'free', cutText:true}},
										  rangeScroll:"fixed", // "fixed" or "free"
										  rangeFacet:"free", // "fixed" or "free"
										  tick:{{size:14, weight:400}},
										  label:{{value:"Topic Keywords", size:14, weight:700}},
										  offset:{{top:0, bottom:10}},
										  show:true,
										  show_line:false,
										  show_ticks:false,
										}},

										font={{family:body_font}},

										margin={{top:10, bottom:10, left:10, right:10, g:10}},

										canvas={{width:1000}},

										zoom=false
									  );


									  // Create table of Top Responses for a Topic when clicking on values in y-axis
									  d3.select("#chart_component_survey_responses_" + (iQuestion+1))
										  .select(".y_axis").selectAll(".tick")
										  .on("click", (event, d) => {{

											  var topic_keywords = event.currentTarget.getAttribute("text_long");

											  d3.select("#chart_component_survey_responses_" + (iQuestion+1)).select("#table_" + (iQuestion+1)).remove();
											  var table = d3.select("#chart_component_survey_responses_" + (iQuestion+1)).append("table").attr("id", "table_" + (iQuestion+1)).style("text-align", "left").style("border", "1px solid white").style("border-collapse", "separate").style("border-spacing", "2px");
											  var thead = table.append("thead")
											  var tbody = table.append("tbody");
											  var columns = ["Response"];

											  // append the header row
											  thead.append("tr")
												  .selectAll("th")
												  .data(["Keywords: " + topic_keywords]).enter()
												  .append("th")
													  .style("background", "#d3d2d2")
													  .style("padding-left", "10px")
													  .style("padding-right", "10px")
													  .style("padding-top", "5px")
													  .style("padding-bottom", "5px")
													  .append("p")
													  .text(function (column) {{ return column; }});

											  // create a row for each object in the data
											  var rows = tbody.selectAll("tr")
												  .data(data_component_survey_responses.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"] && d['topic_keywords'] == topic_keywords).map(d => [d['answer']]))
												  .enter()
												  .append("tr")
													  .attr("valign", "top");


											  // create a cell in each row for each column
											  var cells = rows.selectAll("td")
											  .data(function (row) {{
												return columns.map(function (column, i) {{
												  return {{"column": column, "value": row[i]}};
												}});
											  }})
											  .enter()
											  .append("td")
												  .style("padding-left", "10px")
												  .style("padding-right", "10px")
												  .style("padding-top", "5px")
												  .style("padding-bottom", "5px")
												  .style("min-width", "150px")
												  .style("color", "black")
												  .append("p")
													  .text(function (d, i) {{
														  return d.value;
													   }});

											  d3.selectAll(".user-select-none")
												  .style("overflow", "hidden") ;
										  }});

								}}

								// Non-Topic Analysis questions
								else{{

									var data = data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => [d["answer"], d["dt"]]);
									var total_responses = (data.length == 0 || (data.length == 1 && data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => d["answer"])[0] == "No Responses"))? 0: data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => d["total"])[0];

									d3.select("#chart_component_{0}_" + (iQuestion+1)).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text(vQuestion["question"]);
									d3.select("#chart_component_{0}_" + (iQuestion+1)).append("h2").style("margin", "0").style("text-align", "center").style("color", "black").style("font-weight", "700").text("(" + d3.format(",.0f")(total_responses) + " Responses)");

									if(total_responses > {3} ){{
									   d3.select("#chart_component_{0}_" + (iQuestion+1)).append("p").style("text-align", "center").style("color", "black").style("font-weight", "400").text("The latest 2,000 responses are listed below.");
									}}


									// Add Search Bar
									var search = d3.select("#chart_component_{0}_" + (iQuestion+1))
									.append("div")
									  .style("display", "inline-block")
									  .attr("class", "form-group fg--search")

									search.append("input")
									  .attr("class", "input")
									  .attr("placeholder", "Search")
									  .attr("onkeyup", "searchFunction("+"search_" + (iQuestion+1) +")")
									  .attr("id", "search_" + (iQuestion+1));


									search.append("button")
									  .attr("type", "submit")
									.append("i")
									  .attr("class", "fa fa-search");

									d3.select("#chart_component_{0}_" + (iQuestion+1))
									.append("div")
									  .style("display", "inline-block")
									  .style("margin", "10px")
									  .append("h2")
									  .attr("id", "search_results_" + (iQuestion+1))



									var table = d3.select("#chart_component_{0}_" + (iQuestion+1)).append("table").attr("id", "table_" + (iQuestion+1)).style("text-align", "left").style("border", "1px solid white").style("border-collapse", "separate").style("border-spacing", "2px");
									var thead = table.append("thead")
									var	tbody = table.append("tbody");
									var columns = ["Response", "Date"];

									// append the header row
									thead.append("tr")
										.selectAll("th")
										.data(["Response", "Date"]).enter()
										.append("th")
											.style("background", "#d3d2d2")
											.style("padding-left", "10px")
											.style("padding-right", "10px")
											.style("padding-top", "5px")
											.style("padding-bottom", "5px")
											.append("p")
												.text(function (column) {{ return column; }});

									// create a row for each object in the data
									var rows = tbody.selectAll("tr")
										.data(data)
										.enter()
										.append("tr")
											.attr("valign", "top");

									// create a cell in each row for each column
									var cells = rows.selectAll("td")
									.data(function (row) {{
									  return columns.map(function (column, i) {{
										//bg_color = (column == "NPS Score")? row[2]: "white"; //(i <= 1)?row[3] :"white";
										//font_color = (column == "NPS Score")? row[3]: "black"; //(i <= 1)?row[4] :"black";
										return {{"column": column, "value": row[i]}};
									  }});
									}})
									.enter()
									.append("td")
										.style("padding-left", "10px")
										.style("padding-right", "10px")
										.style("padding-top", "5px")
										.style("padding-bottom", "5px")
										.style("min-width", "150px")
										//.style("background", d => d["bg_color"])
										.style("color", "black")
										.append("p")
											.text(function (d, i) {{
												if(i == 0){{ return d.value; }}
												else{{
												  return d3.timeFormat("%b %d, %Y")(d.value);
												}}
											 }});

									d3.selectAll(".user-select-none")
										//.style("height", 270 + "px")
										.style("overflow", "hidden") ;
								}}

							}}

							// Multiple Choice and Yes/No Questions
							else{{
								var clr_list = Array.from(new Set(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => d["bar_color"])));
								var groupVar = (clr_list.length == 1)? null: "answer";
								var groupType = (clr_list.length == 1)? "group": "stack";
								var yVar = (clr_list.length == 1)? "answer": "question";
								var yShow = (clr_list.length == 1)? true: false;

								chart_bar_horizontal(
									data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]),
									html_id="#chart_component_{0}_" + (iQuestion+1),

									x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
									y={{var:yVar, order:"as_appear", ascending:true}}, // Must be categorical

									title={{value:[
										{{size:17, weight:700, text:vQuestion["question"]}},
										{{size:17, weight:700, text:"(" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["orderid"] == vQuestion["orderid"]).map(d => d["total"])[0]) + " Responses)"}},
									], line:false}},

									clr={{var:"bar_color", value:"#e32726"}}, // Variable containing color of bar(s) or value to set all bars to same color
									opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

									facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
									group={{var:groupVar, label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
									switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
									scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

									bar={{
									size:14, weight:400,
									text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}],
									extra_height:0
									}},

									tooltip_text=[
										{{size:16, weight:700, text:[{{var:"answer", format:null, prefix:null, suffix:null}}]}},
										{{size:16, weight:400, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
										{{size:14, weight:400, text:[
										  {{var:"n", format:",.0f", prefix:null, suffix:null}},
										  {{var:"total", format:",.0f", prefix:" / ", suffix:null}}
										]}}
									],

									barmode=groupType, // "group" or "stack"

									column_data = {{
										before_x:null,
										after_x:null
									}},

									vline={{var:null, value:null}},

									xaxis={{
										range: [null, null],
										rangeScroll:"fixed", // "fixed" or "free"
										rangeFacet:"fixed", // "fixed" or "free"
										suffix: null,
											tick:{{size:14, weight:400}},
											label:{{value:null, size:20, weight:700}},
											offset: {{left:10, right:10}},
											show:false,
											show_line:true,
											show_ticks:true,
											num_ticks:null,
											show_grid:false
										}},

									yaxis={{
										rangeScroll:"fixed", // "fixed" or "free"
										rangeFacet:"fixed", // "fixed" or "free"
										tick:{{size:14, weight:400}},
											label:{{value:null, size:20, weight:700}},
											offset: {{top:10, bottom:10}},
											show:yShow,
											show_line:false,
											show_ticks:false,
										}},

									font={{family:body_font}},


									margin={{top:10, bottom:10, left:10, right:10, g:10}},

									canvas={{width:1000}},

									zoom=false
								);
							}}

						}})



					}}


					'''.format(key2, proj_selector, dmg_selector, srv_comment_limit)

				if key2 == 'proj_engagement':
					# Generate Plotly Express charts server-side for each project
					proj_engagement_df = dict_df['proj']['proj_engagement']
					unique_projects = proj_engagement_df['project'].str.strip().unique()

					# Generate chart data for each project
					proj_chart_data = {}
					proj_summary_html = {}
					for proj_name in unique_projects:
						chart_json, summary_html = create_proj_engagement_chart(proj_engagement_df, proj_name)
						proj_chart_data[proj_name] = chart_json
						proj_summary_html[proj_name] = summary_html

					# Convert to JSON for JavaScript
					import json
					chart_data_js = json.dumps(proj_chart_data)
					summary_html_js = json.dumps(proj_summary_html)

					html_page += '''
					// PROJECT - LEARNER ENGAGEMENT (Plotly Express - Server-side rendered)
					try {{
						console.log("Setting up Project Engagement chart display");
						var parent = document.getElementById("component_content_{0}");
						var existing = document.getElementById("contentsub_{0}");
						if (existing && parent) parent.removeChild(existing);

						var grid = document.createElement("div");
						grid.id = "contentsub_{0}";
						grid.style.display = "grid";
						grid.style.gridTemplateRows = "min-content min-content";
						grid.style.gridTemplateColumns = "1fr";
						grid.style.gridGap = "5px";
						if (parent) parent.appendChild(grid);

						// Create text and chart divs
						var textDiv = document.createElement("div");
						textDiv.id = "text_component_{0}_1";
						textDiv.style.alignSelf = "end";
						grid.appendChild(textDiv);

						var chartDiv = document.createElement("div");
						chartDiv.id = "chart_component_{0}_1";
						chartDiv.style.alignSelf = "start";
						chartDiv.style.width = "100%";
						chartDiv.style.minHeight = "300px";
						grid.appendChild(chartDiv);

						// Store chart data from Python (Plotly Express)
						var projEngagementChartData = {1};
						var projEngagementSummaryHtml = {2};

						// Function to render chart for selected project
						// Function to render chart for selected project
						window.renderProjEngagementChart = function() {{
							var projSelector = document.getElementById("selectProj");
							if (!projSelector) {{
								console.error("Project selector 'selectProj' not found!");
								return;
							}}
							
							var selectedProj = projSelector.value ? projSelector.value.trim() : "";
							console.log("Rendering Chart. Selected Project:", selectedProj);
							console.log("Available Projects in Data:", Object.keys(projEngagementChartData));

							// Update summary text
							if (projEngagementSummaryHtml[selectedProj]) {{
								textDiv.innerHTML = projEngagementSummaryHtml[selectedProj];
							}} else {{
								console.warn("No summary HTML found for project:", selectedProj);
							}}

							// Render Plotly chart
							if (projEngagementChartData[selectedProj]) {{
								console.log("Found chart data for project. Rendering...");
								try {{
									var chartSpec = JSON.parse(projEngagementChartData[selectedProj]);
									Plotly.newPlot(chartDiv.id, chartSpec.data, chartSpec.layout, {{responsive: true}});
								}} catch (e) {{
									console.error("Error parsing or plotting chart data:", e);
								}}
							}} else {{
								console.warn("No chart data found for project:", selectedProj);
								// Debug: print available keys again if mismatch
								console.log("Keys available:", Object.keys(projEngagementChartData));
								console.log("Key looked for:", selectedProj);
								console.log("Comparison result:", Object.keys(projEngagementChartData).includes(selectedProj));
							}}
						}};

						// Render initial chart
						// Wait for DOM content to be loaded just in case, though this script is likely at end of body
						if (document.readyState === 'loading') {{
							document.addEventListener('DOMContentLoaded', window.renderProjEngagementChart);
						}} else {{
							window.renderProjEngagementChart();
						}}

						// Alias for compatibility
						window.updateProjEngagementChart = window.renderProjEngagementChart;
						
						// Add event listener to dropdown if not already handled elsewhere (it seems handled by onchange in HTML)
						var projSelector = document.getElementById("selectProj");
						if (projSelector) {{
							projSelector.addEventListener('change', window.renderProjEngagementChart);
						}}

					}} catch(e) {{
						console.error("Error in Project Engagement Chart:", e);
					}}

					'''.format(key2, chart_data_js, summary_html_js)

				
				if key2 == 'proj_engagement_over_time':
					html_page += '''
					// PROJECT - LEARNER ENGAGEMENT OVER TIME

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();



					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						.append("p")
						.attr("class", "component_text");

					var sing_plur_ovl_{0} = (data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["complete_any_sim"])[0] == 1)? " learner has ": " learners have ";

					d3.select("#text_component_{0}_1").select(".component_text")
					  .append("text")
					  .attr("dx", "0em")
					  .attr("dy", "0em")
						.append("tspan")
						  .style("font-weight", 700)
						  .text(d3.format(",.0f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["complete_any_sim"])[0]))
						.append("tspan")
						  .style("font-weight", 400)
						  .text(sing_plur_ovl_{0} + " completed an attempt of ")
						.append("tspan")
						  .style("font-weight", 700)
						  .text("at least one ")
						.append("tspan")
						  .style("font-weight", 400)
						  .text("Simulation.");


					if(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["complete_any_sim"])[0] > 0){{

						var xaxis_freq_{0} = data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["time_freq"])[0];
							if(xaxis_freq_{0} == "d"){{
								var xaxis_freq_{0} = "Date"
							}}
							else if(xaxis_freq_{0} == "w"){{
								var xaxis_freq_{0} = "Week"
							}}
							else if(xaxis_freq_{0} == "m"){{
								var xaxis_freq_{0} = "Month"
							}}
							else if(xaxis_freq_{0} == "q"){{
								var xaxis_freq_{0} = "Quarter"
							}}
							else if(xaxis_freq_{0} == "y"){{
								var xaxis_freq_{0} = "Year"
							}}


							d3.select("#chart_component_{0}_1").selectAll(".svg-container").remove();
							chart_line(
							  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_cum"] > 0),
							  html_id="#chart_component_{0}_1",

							  x={{var:"dt_char", order:"as_appear", ascending:true}},
							  y={{var:"n", ascending:true, ci:{{lower:null, upper:null}}}}, // Must be numeric

							  title={{value:null, line:false}},

							  clr={{
								var:null,
								palette:"dark24", // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
								value:null
							  }}, // Variable containing color of points/lines
							  line={{show_points:true, width:{{var:null, value:1.5}}, opacity:{{var:null, value:1.0}} }},

							  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:"simname", label:{{value:"Simulation:", size:14, weight:700}}, size:14, weight:400, order:"sim_order", ascending:true, show:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  tooltip_text=[
								{{size:14, weight:400, text:[{{var:"n", format:",.0f", prefix:null, suffix:null}}]}},
							  ],

							  xaxis={{
								type:"category", //"numeric" or "category" or "time"
								label:{{value:xaxis_freq_{0}, size:14, weight:700}},
								offset:{{left:10, right:10}},
								range:[null, null],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:null,
								format:null,
								tick:{{size:14, weight:400, orientation:"v", splitWidth:250}},
								show:true,
								show_line:false,
								show_ticks:false,
								num_ticks:null,
								show_grid:false
							  }},

							  yaxis={{
								height:400,
								label:{{value:"Number of Learners", size:14, weight:700}},
								offset:{{top:10, bottom:10}},
								range:[0, null],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								suffix:null,
								format:",.0f",
								tick:{{size:12, weight:400, width:250}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:Math.min(7, (d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["n"])))+1),
								show_grid:true
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:1000}},

							  zoom=false
							);

					}}

					'''.format(key2, dmg_selector)

				if key2 == 'proj_performance_comparison_sim':
					html_page += '''
					// PERFORMANCE IN SHARED SKILLS ACROSS SIMS
					// Remove the existing element with ID "contentsub_proj_performance_comparison_sim" if it exists
					d3.select("#contentsub_{0}").remove();

					// Create a 2x1 grid container inside "component_content_proj_performance_comparison_sim"
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					// Append two child divs to the grid container
					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");
					
					// Remove any existing SVG elements inside the chart container
					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// Check if the dataset has any matching records for the selected project
					if(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).length > 0){{
					
						// Remove existing chart elements inside the chart container
						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						
						// Generate a horizontal bar chart with the filtered dataset
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

							//X-axis configuration: Average Skill Score
						  x={{var:"avg_skillscore", // average skill score // Must be numeric
						  ascending:true, // Sort bars in ascending order based on learner count
						  ci:[null, null]}}, // No confidence interval is applied
							//Y-axis configuration: simulation names
						  y={{var:"simname", // The variable representing the simulation names // Must be categorical
						  order:"as_appear", // Maintain the order as they appear in the dataset
						  ascending:true}}, // Display simulations in ascending order

						  title={{value:null, // No title is displayed
						  line:true}}, // No underline for the title
						  
							// Color configuration for the bars // Variable containing color of bar(s) or value to set all bars to same color
						  clr={{var:null, // Color variable from the dataset
							palette:null,  // No color palette chosen
							value:"#9fdf9f", // Colors remain unchanged
						  }}, // Variable containing color of points/lines
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							// Faceting to group data by Simulation names // This displays above the bars
						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
						  // Grouping configuration
						  group={{var:null, label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:"demog_val", label:{{value:"Business:", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  scroll={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:true}},

							// Bar configuration
						  bar={{
							size:12, weight:400,
							text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}],
							extra_height:0,
							space_between:0
						  }},

							// Tooltip configuration. // what displays when mouse hovers over the bar
						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"avg_skillscore", format:',.1f', prefix:null, suffix:"%"}}]}},
							{{size:12, weight:400, text:[{{var:"n", format:',.0f', prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  barmode="group", // 'group' or 'stack'

							// Column data // any data displaying before the column
						  column_data = {{
							before_x:{{var:"n", format:",.0f", prefix:null, suffix:null, size:12, weight:400, color:{{var:null, value:"black"}}, label:{{value:"No. of Learners", size:10, weight:700, padding:{{top:5, bottom:0}}}}}},
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

							// X-axis settings
						  xaxis={{
							  range:[0, 100],
							  rangeScroll:"fixed",
							  rangeFacet:"fixed",
							  format:",.0f",
							  suffix:"%",
							  tick:{{size:12, weight:400, orientation:'h', splitWidth:150}},
							  label:{{value:"Average Simulation Performance", size:14, weight:700}},
							  offset:{{left:10, right:10}},
							  show:true,
							  show_line:false,
							  show_ticks:true,
							  num_ticks:6, // change her for number of vertical lines in the plot
							  show_grid:true
						  }},
						  
							// Y-axis settings
						  yaxis={{
							  widthPct:{{value:0.4, range:"free"}},
							  rangeScroll:"fixed",
							  rangeFacet:"fixed",
							  tick:{{size:14, weight:700}},
							  label:{{value:"Simulation", size:14, weight:700}},
							  offset:{{top:10, bottom:10}},
							  show:true,
							  show_line:false,
							  show_ticks:false
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, proj_selector, dmg_selector)
				

				if key2 == 'proj_learner_counts_comparison_sim':
					
					html_page += '''
					// LEARNER COUNTS SIM COMPARISON
					// Remove the existing learner count comparison component if it exists
					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->  Create a new container for the learner count comparison within the specified component
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");
					  
					// Create a text container
					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					// Append a paragraph inside the text container
					d3.select("#text_component_{0}_1").append("p").attr("class", "component_text");
					
					// Remove any existing SVG charts inside the chart container
					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// Filter the dataset based on selected demographic variable and value
					let filteredData = data_component_proj_learner_counts_comparison_sim.filter(d => 
						d["project"] == projSelector.value);

					// Check if any learners exist in the filtered dataset
					if(d3.sum(filteredData.map(d => d["n"])) === 0){{
						// Display a message if no learners are found
						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("No Simulation has any Learners.");
					}}
					else{{
						// Check if the project filter is applied
						let projectFilteredData = filteredData.filter(d => d["project"] == projSelector.value);
					
						if(data_component_proj_learner_counts_comparison_sim.filter(d => d["project"] == projSelector.value)){{
							// Remove any existing SVG charts
							d3.select("#chart_component_{0}_1").selectAll(".svg-container").remove();
							
							// 🔹 Render the stacked horizontal bar chart
							chart_bar_horizontal(
							// filter the data to the project selected
							  data=data_component_{0}.filter(d => d["project"] == projSelector.value),
							  html_id="#chart_component_{0}_1",

							// X-axis configuration: learner count values
							  x={{var:"n", // number of learners // Must be numeric
							  ascending:true, // Sort bars in ascending order based on learner count
							  ci:[null, null]}}, // No confidence interval is applied

							  // Y-axis configuration: simulation names
							  y={{var:"simname", // The variable representing the simulation names // Must be categorical
							  order:"as_appear",  // Maintain the order as they appear in the dataset
							  ascending:true}}, // Display simulations in ascending order

							  title={{value:null, // No title is displayed
							  line:false}}, // No underline for the title
							  
							// Color configuration for the bars // Variable containing color of bar(s) or value to set all bars to same color
							  clr={{var:"bar_color", // Color variable from the dataset
							  palette:null, // No color palette chosen
							  value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity
							   
								// Faceting to group data by Simulation names // This displays above the bars
							  facet={{var:null, size:16, weight:700, space_above_title:10, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  
							  // Grouping configuration
							  group={{var:"demog_val", label:{{value:"Business: ", size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
							  switcher={{var:null, label:{{value:null, size:14, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

								// Bar styling
							  bar={{
								size:12, weight:400,
								text:[
									{{var:"n", format:",.0f", prefix:null, suffix:null}},],
								extra_height:0,
								space_between:10
							  }},
							  
								// Tooltip setting // what displays when the mouse hovers over the bar
							  tooltip_text=[
								{{size:14, weight:700, text:[{{var:"demog_val", format:null, prefix:null, suffix:null}}]}},
								{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								{{size:14, weight:700, text:[{{var:"n", format:null, prefix:"Learner count: ", suffix:null}}]}},
							  ],

							  barmode="stack", // "group", "stack" or "overlay"

								// Column data // any data displaying in the column
							  column_data = {{
								before_x:null,
								after_x:{{var:null, format:",.0f", prefix:null, suffix:null, size:14, weight:700, color:{{var:null, value:null}},
								label:{{value:null, size:16, weight:700, padding:{{top:10, bottom:0}}}}}}
							  }},

							  vline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								range: [0, d3.max(filteredData, d => d["max_value"])],
								rangeScroll:"free", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								format:",.0f",
								suffix:null,
								tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
								label:{{value:"Number of Learners", size:14, weight:700}},
								offset:{{left:10, right:10}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:10, // change here for number of vertical lines in the plot.
								show_grid:true
							  }},

							  yaxis={{
								widthPct:{{value:0.4, range:"free"}},
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"free", // "fixed" or "free"
								tick:{{size:14, weight:700}}, // set tick size and weight that displays
								label:{{value:"Simulation", size:14, weight:700}},
								offset:{{top:0, bottom:10}},
								show:true,
								show_line:false,
								show_ticks:false,
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:1000}},

							  zoom=false
							);
						}}

					}}

					'''.format(key2, dmg_selector)

				if key2 == 'proj_overall_pass_rates':
					html_page += '''
					// OVERALL PASS RATES BY SIM

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#text_component_{0}_1")
						.append("p")
						.attr("class", "component_text");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					if(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["n_skills"])) == 0){{

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("No Simulation has a Pass/Fail setting.");

					}}

					else if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["total"])) == 0){{

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("0")
							.append("tspan")
								.style("font-weight", 400)
								.text(" learners have completed an attempt of a Simulation that has a Pass/Fail setting.");

					}}

					else{{

						Array.from(new Set(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["simname"]))).forEach((v, i) => {{

							if(i > 0){{
								d3.select("#text_component_{0}_1").select(".component_text").append("br");
							}}

							//d3.select("#text_component_{0}_1").select(".component_text").append("br");

							d3.select("#text_component_{0}_1").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "0em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(numFormat(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == v).map(d => d["pct"]))) + "% ")
								.append("tspan")
								  .style("font-weight", 700)
								  .text("(" + d3.format(",.0f")(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == v).map(d => d["n"]))) + " out of " +  d3.format(",.0f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == v).map(d => d["total"])[0]) + ") ")
								.append("tspan")
								  .style("font-weight", 400)
								  .text(" of learners have passed an attempt of ")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(v)
								.append("tspan")
								  .style("font-weight", 400)
								  .text(".");
						}})


						Array.from(new Set(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] == 0).map(d => d["simname"]))).forEach((v, i) => {{

							if(i == 0){{
								d3.select("#text_component_{0}_1").select(".component_text").append("br");
							}}

							d3.select("#text_component_{0}_1").select(".component_text").append("br");

							d3.select("#text_component_{0}_1").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "0em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(v)
								.append("tspan")
								  .style("font-weight", 400)
								  .text(" has no Pass/Fail setting.");
						}})


						if( d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total"])) > 0 && d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["total"])) > 0){{

							d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
							chart_bar_horizontal(
							  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0),
							  html_id="#chart_component_{0}_1",

							  x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
							  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

							  title={{value:null, line:false}},

							  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:"stat", label:{{value:"Attempts needed to Pass:", size:14, weight:700}}, size:14, weight:400, order:"alphabetical", ascending:true, show:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  bar={{
								size:14, weight:400,
								text:[
									{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
								],
								extra_height:0,
								space_between:14
							  }},

							  tooltip_text=[
								{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
								{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								{{size:14, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:" Attempt(s)"}}]}},
								{{size:14, weight:400, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								{{size:14, weight:400, text:[
									{{var:"n", format:",.0f", prefix:"(", suffix:" / "}},
									{{var:"total", format:",.0f", prefix:null, suffix:")"}},
								]}}
							  ],

							  barmode="stack", // "group", "stack" or "overlay"

							  column_data={{
								before_x:{{var:"total", format:',.0f', prefix:null, suffix:null, size:14, weight:400, color:{{var:null, value:"black"}}, label:{{value:"No. of Learners", size:12, weight:700, padding:{{top:0, bottom:0}}}}}},
								after_x:{{var:"total_pass_rate", format:',.1f', prefix:null, suffix:"%", size:14, weight:700, color:{{var:null, value:"black"}}, label:{{value:"Total Pass Rate", size:12, weight:700, padding:{{top:0, bottom:0}}}}}}
							  }},

							  vline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								range: [0, 100],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								format:",.0f",
								suffix:"%",
								tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
								label:{{value:"Percent of Learners", size:14, weight:700}},
								offset:{{left:10, right:10}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:6,
								show_grid:true
							  }},

							  yaxis={{
								widthPct:{{value:0.4, range:"free"}},
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								tick:{{size:14, weight:700}},
								label:{{value:"Simulation", size:14, weight:700}},
								offset:{{top:0, bottom:10}},
								show:true,
								show_line:false,
								show_ticks:false,
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:1000}},

							  zoom=false
							);
						}}

					}}


					'''.format(key2, dmg_selector)


				if key2 == 'proj_skill_pass_rates':
					html_page += '''
					// SKILL PASS RATES BY SIM

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#text_component_{0}_1")
						.append("p")
						.attr("class", "component_text");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					if(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["n_skills"])) == 0){{

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							  .append("tspan")
								.style("font-weight", 400)
								.text("No Simulation has any Pass/Fail settings.");

					}}

					else if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["total"])) == 0){{

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("0")
							.append("tspan")
								.style("font-weight", 400)
								.text(" learners have completed an attempt of a Simulation that has Pass/Fail settings.");

					}}

					else{{

						/*
						var sing_plur_ovl_{0} = (data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["complete_any_sim"])[0] == 1)? " learner has ": " learners have ";

						d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							.append("tspan")
							  .style("font-weight", 700)
							  .text(d3.format(",.0f")(data_component_{0}.map(d => d["complete_any_sim"])[0]))
							.append("tspan")
							  .style("font-weight", 400)
							  .text(sing_plur_ovl_{0} + " completed an attempt of ")
							.append("tspan")
							  .style("font-weight", 700)
							  .text("at least one ")
							.append("tspan")
							  .style("font-weight", 400)
							  .text("Simulation that has a Pass/Fail setting on multiple Skills.");
						*/


						/*
						Array.from(new Set(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["simname"]))).forEach((vSim, iSim) => {{

							d3.select("#text_component_{0}_1").select(".component_text").append("br");
							d3.select("#text_component_{0}_1").select(".component_text").append("br");

							d3.select("#text_component_{0}_1").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "0em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(vSim + " (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == vSim).map(d => d["total"])[0]) + " learners):");


							Array.from(new Set(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0 && d["simname"] == vSim).map(d => d["skillname"]))).forEach((vSkill, iSkill) => {{

								d3.select("#text_component_{0}_1").select(".component_text").append("br");

								d3.select("#text_component_{0}_1").select(".component_text")
								  .append("text")
								  .attr("dx", "0em")
								  .attr("dy", "0em")
									.append("tspan")
									  .style("font-weight", 700)
									  .text(numFormat(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == vSim && d["skillname"] == vSkill).map(d => d["pct"]))) + "% ")
									.append("tspan")
									  .style("font-weight", 700)
									  .text("(" + d3.format(",.0f")(d3.sum(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["simname"] == vSim && d["skillname"] == vSkill).map(d => d["n"]))) +")" )
									.append("tspan")
									  .style("font-weight", 400)
									  .text(" of learners have passed ")
									.append("tspan")
									  .style("font-weight", 700)
									  .text(vSkill)
									.append("tspan")
									  .style("font-weight", 400)
									  .text(" in an attempt.");
							}});
						}});
						*/


						Array.from(new Set(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] == 0).map(d => d["simname"]))).forEach((v, i) => {{

							if(i == 0){{
								d3.select("#text_component_{0}_1").select(".component_text").append("br");
							}}

							d3.select("#text_component_{0}_1").select(".component_text").append("br");

							d3.select("#text_component_{0}_1").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "0em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(v)
								.append("tspan")
								  .style("font-weight", 400)
								  .text(" does not have a Pass/Fail setting on any Skill.");
						}})




						if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0).map(d => d["total"])) > 0){{

							d3.select("#chart_component_{0}_1").selectAll(".svg-container").remove();
							chart_bar_horizontal(
							  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value && d["n_skills"] > 0),
							  html_id="#chart_component_{0}_1",

							  x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
							  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

							  title={{value:null, line:false}},

							  clr={{var:"bar_color", palette:null, value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							  facet={{var:"simname_total", size:16, weight:700, space_above_title:10, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:"stat", label:{{value:"Attempts needed to Pass:", size:14, weight:700}}, size:14, weight:400, order:"alphabetical", ascending:true, show:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  bar={{
								size:14, weight:400,
								text:[
									{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
								],
								extra_height:0,
								space_between:10
							  }},

							  tooltip_text=[
								{{size:14, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
								{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
								{{size:14, weight:700, text:[
									{{var:"stat", format:null, prefix:null, suffix:null}},
									{{var:"stat_suffix", format:null, prefix:" ", suffix:":"}},
								]}},
								{{size:14, weight:700, text:[{{var:"pct", format:",.1f", prefix:null, suffix:"%"}}]}},
								{{size:14, weight:400, text:[
									{{var:"n", format:",.0f", prefix:"(", suffix:null}},
									{{var:"total", format:",.0f", prefix:" out of ", suffix:" Learners)"}},
									]
								}},
							  ],

							  barmode="stack", // "group", "stack" or "overlay"

							  column_data = {{
								before_x:null,
								after_x:{{var:"total_pct", format:",.1f", prefix:null, suffix:"%", size:14, weight:700, color:{{var:null, value:"#339933"}}, label:{{value:"Total Pass Rate", size:12, weight:700, padding:{{top:10, bottom:0}}}}}}
							  }},

							  vline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								range: [0, 100],
								rangeScroll:"free", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								format:",.0f",
								suffix:"%",
								tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
								label:{{value:"Percent of Learners", size:14, weight:700}},
								offset:{{left:10, right:10}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:6,
								show_grid:true
							  }},

							  yaxis={{
								widthPct:{{value:0.35, range:"free"}},
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"free", // "fixed" or "free"
								tick:{{size:14, weight:400}},
								label:{{value:"Skill", size:14, weight:700}},
								offset:{{top:0, bottom:10}},
								show:true,
								show_line:false,
								show_ticks:false,
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:1000}},

							  zoom=false
							);
						}}

					}}


					'''.format(key2, dmg_selector)


				if key2 == 'proj_time_spent':

					html_page += '''
					// TIME SPENT IN TASK MODE BY SIM

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total"])) > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"avg_cum_duration", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:null, label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:14, weight:400,
							text:[
								{{var:"avg_cum_duration", format:",.1f", prefix:null, suffix:null}},
							],
							extra_height:0,
							space_between:14
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"avg_cum_duration", format:",.1f", prefix:null, suffix:" minutes"}}]}},
							{{size:14, weight:400, text:[{{var:"total", format:",.0f", prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  barmode="group", // "group", "stack" or "overlay"

						  column_data={{
							before_x:{{var:"total", format:',.0f', prefix:null, suffix:null, size:14, weight:400, color:{{var:null, value:"black"}}, label:{{value:"No. of Learners", size:12, weight:700, padding:{{top:0, bottom:0}}}}}},
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

						  xaxis={{
							range:[0, Math.ceil(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["avg_cum_duration"]))/ 60)*60 ],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix:null,
							tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
							label:{{value:"Average Time to Complete all Attempts (mins)", size:14, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:7,
							show_grid:true
						  }},

						  yaxis={{
							widthPct:{{value:0.4, range:"free"}},
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:14, weight:700}},
							label:{{value:"Simulation", size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, dmg_selector)


				if key2 == 'proj_practice_mode':
					html_page += '''
					// PRACTICE MODE BY SIM

					d3.select("#contentsub_{0}").remove();

					// --- 2x2 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr 1fr")
					  .style("grid-gap", "5px")
					  .style("margin-bottom", "20px");


					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "text_component_{0}_2").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "chart_component_{0}_1").style("align-self", "start");
					d3.select("#contentsub_{0}").append("div").attr("class", "grid__item").attr("id", "chart_component_{0}_2").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
					d3.select("#chart_component_{0}_2").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total"])) == 0){{

					  d3.select("#text_component_{0}_1").select(".component_text")
						  .append("text")
						  .attr("dx", "0em")
						  .attr("dy", "0em")
							 .append("tspan")
								.style("font-weight", 700)
								.text("0")
							.append("tspan")
							  .style("font-weight", 400)
							  .text(" learners have completed an attempt of any Simulation.");

					}}
					else{{

						// --- First Chart Grid Element --->
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:null, value:"#339933"}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:null, label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:12, weight:400,
							text:[
								{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
							],
							extra_height:0,
							space_between:5
						  }},

						  tooltip_text=[
							{{size:14, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:12, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
							{{size:12, weight:400, text:[
							  {{var:"n", format:",.0f", prefix:"(", suffix:null}},
							  {{var:"total", format:",.0f", prefix:" out of ", suffix:" Learners)"}}
							]}}
						  ],

						  barmode="group", // "group", "stack" or "overlay"

						  column_data={{
							before_x:null,
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

						  xaxis={{
							range:[0, 100],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix:"%",
							tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
							label:{{value:"% of Learner accessing Practice Mode", size:12, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:7,
							show_grid:true
						  }},

						  yaxis={{
							widthPct:{{value:0.4, range:"free"}},
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:12, weight:700}},
							label:{{value:null, size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:500}},

						  zoom=false
						);



						if(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["n"])) > 0){{

							// --- Second Chart Grid Element --->
							chart_bar_horizontal(
							  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
							  html_id="#chart_component_{0}_2",

							  x={{var:"avg_practice_duration", ascending:true, ci:[null, null]}}, // Must be numeric
							  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

							  title={{value:null, line:false}},

							  clr={{var:null, value:"#1f77b4"}}, // Variable containing color of bar(s) or value to set all bars to same color
							  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

							  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
							  group={{var:null, label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
							  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
							  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

							  bar={{
								size:12, weight:400,
								text:[
									{{var:"avg_practice_duration", format:",.1f", prefix:null, suffix:null}},
								],
								extra_height:0,
								space_between:5
							  }},

							  tooltip_text=[
								{{size:14, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
								{{size:12, weight:700, text:[{{var:"avg_practice_duration", format:".1f", prefix:"Average: ", suffix:" mins"}}]}},
								{{size:12, weight:400, text:[
								  {{var:"n", format:",.0f", prefix:"(", suffix:" Learners)"}}
								]}}
							  ],

							  barmode="group", // "group", "stack" or "overlay"

							  column_data={{
								before_x:null,
								after_x:null
							  }},

							  vline={{
								var:null,
								value:null
							  }},

							  xaxis={{
								range:[0, Math.ceil(d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["avg_practice_duration"]))/ 60)*60 ],
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								format:",.0f",
								suffix:null,
								tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
								label:{{value:"Time Spent in Practice Mode (mins)", size:12, weight:700}},
								offset:{{left:10, right:10}},
								show:true,
								show_line:false,
								show_ticks:true,
								num_ticks:7,
								show_grid:true
							  }},

							  yaxis={{
								widthPct:{{value:0.4, range:"free"}},
								rangeScroll:"fixed", // "fixed" or "free"
								rangeFacet:"fixed", // "fixed" or "free"
								tick:{{size:12, weight:700}},
								label:{{value:null, size:14, weight:700}},
								offset:{{top:0, bottom:10}},
								show:true,
								show_line:false,
								show_ticks:false,
							  }},

							  font={{family:body_font}},

							  margin={{top:10, bottom:10, left:10, right:10, g:10}},

							  canvas={{width:500}},

							  zoom=false
							);

						}}
					}}


					'''.format(key2, dmg_selector)


				if key2 == 'proj_shared_skill_polar':

					html_page += '''
					// PERFORMANCE IN SHARED SKILLS ACROSS SIMS

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).length > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_polar(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"avg_skillscore", ci:{{lower:null, upper:null}}}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:true}},

						  clr={{
							var:null,
							palette:'dark24', // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
							value:null
						  }}, // Variable containing color of points/lines
						  line={{width:2, opacity:1.0}}, // Values of width and opacity of lines

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true}},
						  group={{var:"simname", label:{{value:"Simulation:", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true}},
						  switcher={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:true}},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"avg_skillscore", format:',.1f', prefix:null, suffix:"%"}}]}},
							{{size:12, weight:400, text:[{{var:"n", format:',.0f', prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  xaxis={{
							range:[0, 100],
							suffix:"%",
							format:",.0f",
							tick:{{size:10, weight:400}},
							show:true,
							num_ticks:6
						  }},

						  yaxis={{
							height:400,
							offset:{{top:10, bottom:10}},
							tick:{{size:14, weight:400, width:200}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, dmg_selector)


				if key2 == 'proj_shared_skill_bar':

					html_page += '''
					// PERFORMANCE IN SHARED SKILLS ACROSS SIMS

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).length > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"avg_skillscore", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:true}},

						  clr={{
							var:null,
							palette:"dark24", // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
							value:null
						  }}, // Variable containing color of points/lines
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
						  group={{var:"simname", label:{{value:"Simulation:", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:true}},

						  bar={{
							size:12, weight:400,
							text:[{{var:"avg_skillscore", format:",.1f", prefix:null, suffix:"%"}}],
							extra_height:0,
							space_between:5
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"avg_skillscore", format:',.1f', prefix:null, suffix:"%"}}]}},
							{{size:12, weight:400, text:[{{var:"n", format:',.0f', prefix:"(", suffix:" Learners)"}}]}}
						  ],

						  barmode="group", // 'group' or 'stack'

						  column_data = {{
							before_x:{{var:"n", format:",.0f", prefix:null, suffix:null, size:12, weight:400, color:{{var:null, value:"black"}}, label:{{value:"No. of Learners", size:10, weight:700, padding:{{top:5, bottom:0}}}}}},
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

						  xaxis={{
							  range:[0, 100],
							  rangeScroll:"fixed",
							  rangeFacet:"fixed",
							  format:",.0f",
							  suffix:"%",
							  tick:{{size:12, weight:400, orientation:'h', splitWidth:150}},
							  label:{{value:"Avg. Skill Performance", size:14, weight:700}},
							  offset:{{left:10, right:10}},
							  show:true,
							  show_line:false,
							  show_ticks:true,
							  num_ticks:6,
							  show_grid:true
						  }},

						  yaxis={{
							  widthPct:{{value:0.4, range:"free"}},
							  rangeScroll:"fixed",
							  rangeFacet:"fixed",
							  tick:{{size:14, weight:700}},
							  label:{{value:"Skill", size:14, weight:700}},
							  offset:{{top:10, bottom:10}},
							  show:true,
							  show_line:false,
							  show_ticks:false
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, dmg_selector)

				if key2 == 'proj_nps':
					html_page += '''
					// NPS SCORE BY SIM

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// --- First Chart Grid Element --->
					chart_bar_horizontal(
					  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
					  html_id="#chart_component_{0}_1",

					  x={{var:"pct", ascending:true, ci:[null, null]}}, // Must be numeric
					  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

					  title={{value:null, line:false}},

					  clr={{var:"bar_color", palette:null, value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
					  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

					  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
					  group={{var:"answer", label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"alphabetical", ascending:false, show:true}},
					  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
					  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

					  bar={{
						size:14, weight:400,
						text:[
							{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
						],
						extra_height:0,
						space_between:5
					  }},

					  tooltip_text=[
						{{size:14, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
						{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
						{{size:14, weight:700, text:[{{var:"answer", format:null, prefix:null, suffix:null}}]}},
						{{size:12, weight:700, text:[{{var:"pct", format:".1f", prefix:null, suffix:"%"}}]}},
						{{size:12, weight:400, text:[
						  {{var:"n", format:",.0f", prefix:"(", suffix:null}},
						  {{var:"total", format:",.0f", prefix:" out of ", suffix:" Learners)"}}
						]}}
					  ],

					  barmode="stack", // "group", "stack" or "overlay"

					  column_data={{
						before_x:{{var:"total", format:",.0f", prefix:null, suffix:null, size:14, weight:400, color:{{var:null, value:"black"}}, label:{{value:"No. of Learners", size:12, weight:700, padding:{{top:0, bottom:0}}}}}},
						after_x:{{var:"avg_nps_score", format:'+.2f', prefix:null, suffix:null, size:14, weight:700, color:{{var:null, value:"black"}}, label:{{value:"NPS Score", size:12, weight:700, padding:{{top:0, bottom:0}}}}}}
					  }},

					  vline={{
						var:null,
						value:null
					  }},

					  xaxis={{
						range:[0, 100],
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						format:",.0f",
						suffix:"%",
						tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
						label:{{value:null, size:12, weight:700}},
						offset:{{left:10, right:10}},
						show:false,
						show_line:false,
						show_ticks:true,
						num_ticks:7,
						show_grid:true
					  }},

					  yaxis={{
						widthPct:{{value:0.4, range:"free"}},
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						tick:{{size:14, weight:700}},
						label:{{value:"Simulation", size:14, weight:700}},
						offset:{{top:0, bottom:10}},
						show:true,
						show_line:false,
						show_ticks:false,
					  }},

					  font={{family:body_font}},

					  margin={{top:10, bottom:10, left:10, right:10, g:10}},

					  canvas={{width:1000}},

					  zoom=false
					);


					'''.format(key2, dmg_selector)
				
				if key2 == 'proj_seat_time':
					html_page += '''
					// TIME SEAT REDUCTION
					// Remove the existing element with ID "contentsub_proj_seat_time" if it exists

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_{0}_1")
						  .append("p")
						  .attr("class", "component_text");


					var filtered_data=data_component_{0}.filter(d => d["project"] == projSelector.value & d['simname'] != "Total");

					chart_bar_horizontal(
					  data=filtered_data,
					  html_id="#chart_component_{0}_1",

					  x={{var:"total", ascending:true, ci:[null, null]}}, // Must be numeric
					  y={{var:"diagnostic", order:"as_appear", ascending:true}}, // Must be categorical

					  title={{value:null, line:false}},

					  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
					  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

					  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, 
					  line:{{show:false, color:'#d3d2d2'}}}},
					  group={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", 
					  ascending:true, show:true}},
					  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", 
					  ascending:true, line:false}},
					  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", 
					  ascending:true, line:false}},

					  bar={{
						size:12, weight:400,
						text:[{{var:"total", format:",.2f", prefix:null, suffix:null}}],
						extra_height:0,
						space_between:14
					  }},

					  tooltip_text=[
						{{size:16, weight:700, text:[{{var:'simname', format:null, prefix:null, suffix:null}}]}},
						{{size:10, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
						{{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
						{{size:14, weight:400, text:[{{var:"pct", format:",.2f", prefix:"(", suffix:null}}]}}
					  ],

					  barmode='group', // 'group' or 'stack'

					  column_data={{
						before_x:null,
						after_x:{{var:"pct", format:'+.2f', prefix:null, suffix:"%", size:14, weight:700, color:{{var:null, value:"#339933"}}, label:{{value:"Average Time Improvement", size:12, weight:700, padding:{{top:0, bottom:0}}}}}}
					  }},

					  vline={{
						var:null,
						value:null
					  }},

					  xaxis={{
						range:[0, null],
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						format:",.0f",
						suffix:null,
						tick:{{size:10, weight:400, orientation:'h', splitWidth:150}},
						label:{{value:"Total Time Seat Savings (hours)", size:14, weight:700}},
						offset:{{left:10, right:10}},
						show:true,
						show_line:false,
						show_ticks:true,
						num_ticks:Math.min(7, (d3.max(filtered_data.map(d => d.total))) + 1),
						show_grid:true
					  }},

					  yaxis={{
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						tick:{{size:14, weight:700}},
						label:{{value:"Simulation", size:14, weight:700}},
						offset:{{top:0, bottom:10}},
						show:true,
						show_line:true,
						show_ticks:true,
						num_ticks: 5,
						show_grid:true,
					  }},

					  font={{family:body_font}},

					  margin={{top:10, bottom:10, left:10, right:10, g:10}},

					  canvas={{width:1000}},

					  zoom=false
					  
					);
					
					// second plot with Total only!
					// --- 2x1 Grid --->
					d3.select("#component_content_{0}")
					  .append("div")
					  .attr("id", "contentsub_proj_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_proj_{0}").append("div").attr("id", "text_component_proj_{0}_2").style("align-self", "end");
					d3.select("#contentsub_proj_{0}").append("div").attr("id", "chart_component_proj_{0}_2").style("align-self", "start");

					d3.select("#chart_component_proj_{0}_2").selectAll('.svg-container').remove();

					// --- First Text Grid Element --->
					d3.select("#text_component_proj_{0}_2")
						  .append("p")
						  .attr("class", "component_text");
					
					var total_data=data_component_proj_{0}.filter(d => d["project"] == projSelector.value & d['simname'] == "Total");

					chart_bar_horizontal(
					  data=total_data,
					  html_id="#chart_component_proj_{0}_2",

					  x={var:"total", ascending:true, ci:[null, null]}, // Must be numeric
					  y={var:"bar_label", order:"as_appear", ascending:true}, // Must be categorical

					  title={value:null, line:false},

					  clr={var:"bar_color", value:null}, // Variable containing color of bar(s) or value to set all bars to same color
					  opacity={var:null, value:1.0}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

					  facet={var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, 
					  line:{show:false, color:'#d3d2d2'}},
					  group={var:"attempt", label:{value:null, size:18, weight:700}, size:14, weight:400, order:"as_appear", 
					  ascending:true, show:true},
					  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:"as_appear", 
					  ascending:true, line:false},
					  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:"as_appear", 
					  ascending:true, line:false},

					  bar={
						size:12, weight:400,
						text:[{var:"total", format:",.2f", prefix:null, suffix:null}],
						extra_height:0,
						space_between:14
					  },

					  tooltip_text=[
						{size:16, weight:700, text:[{var:'simname', format:null, prefix:null, suffix:null}]},
						{size:10, weight:700, text:[{var:null, format:null, prefix:null, suffix:null}]},
						{size:14, weight:700, text:[{var:null, format:null, prefix:null, suffix:null}]},
						{size:14, weight:400, text:[{var:"pct", format:",.2f", prefix:"(", suffix:null}]}
					  ],

					  barmode='group', // 'group' or 'stack'

					  column_data={
						before_x:null,
						after_x:{var:"pct", format:'+.2f', prefix:null, suffix:"%", size:14, weight:700, color:{var:null, value:"#339933"}, label:{value:"Average Time Improvement", size:12, weight:700, padding:{top:0, bottom:0}}}
					  },

					  vline={
						var:null,
						value:null
					  },

					  xaxis={
						range:[0, null],
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						format:",.0f",
						suffix:null,
						tick:{size:10, weight:400, orientation:'h', splitWidth:150},
						label:{value:"Total Time Seat Savings (hours)", size:14, weight:700},
						offset:{left:10, right:10},
						show:true,
						show_line:false,
						show_ticks:true,
						num_ticks:Math.min(7, (d3.max(total_data.map(d => d.total))) + 1),
						show_grid:true
					  },

					  yaxis={
						rangeScroll:"fixed", // "fixed" or "free"
						rangeFacet:"fixed", // "fixed" or "free"
						tick:{size:14, weight:700},
						label:{value:"Simulation", size:14, weight:700},
						offset:{top:0, bottom:10},
						show:true,
						show_line:true,
						show_ticks:true,
						num_ticks: 5,
						show_grid:true,
					  },

					  font={family:body_font},

					  margin={top:10, bottom:10, left:10, right:10, g:10},

					  canvas={width:1000},

					  zoom=false
					  
					);


					'''.format(key2, proj_selector)
					
				if key2 == 'dmg_engagement':
					html_page += '''
					// DEMOGRAPHICS - LEARNER ENGAGEMENT

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();



					// --- First Text Grid Element --->
					/*
					d3.select("#text_component_{0}_1")
						.append("p")
						.attr("class", "component_text");

					d3.select("#text_component_{0}_1").select(".component_text")
					  .append("text")
					  .attr("dx", "0em")
					  .attr("dy", "0em")
						.append("tspan")
						  .style("font-weight", 700)
						  .text(d3.format(",.0f")(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["_total"])[0]))
						.append("tspan")
						  .style("font-weight", 400)
						  .text(" learners have completed an attempt of the Simulation.");
					*/



					/*if(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["_total"])[0] > 0){{*/

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
						  data=data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value && d["stat"] == "Completed"),
						  html_id="#chart_component_{0}_1",

						  x={{var:"_n", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:selected_filter, order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:"stat", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:14, weight:400,
							text:[
								{{var:"_n", format:",.0f", prefix:null, suffix:null}},
								//{{var:"_pct", format:",.1f", prefix:"(", suffix:"%)"}},
							],
							extra_height:0,
							space_between:10
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:selected_filter, format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:16, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"_n", format:",.0f", prefix:null, suffix:" Learners"}}]}},
							//{{size:14, weight:400, text:[{{var:"_pct", format:",.1f", prefix:"(", suffix:"%)"}}]}}
						  ],

						  barmode="overlay", // "group", "stack" or "overlay"

						  column_data = {{
							before_x:null,
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

						  xaxis={{
							range: [0, null],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix:null,
							tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
							label:{{value:"Number of Learners", size:14, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:Math.min(7, (d3.max(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["_n"])))+1),
							show_grid:true
						  }},

						  yaxis={{
							widthPct:{{value:0.4, range:"free"}},
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:14, weight:700}},
							label:{{value:selected_filter, size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					/*}}*/


					'''.format(key2, proj_selector)


				if key2 == 'dmg_skill_baseline':
					html_page += '''
					// DEMOGRAPHICS - SKILL PERFORMANCE BASELINE

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();



					// --- First Text Grid Element --->
					/*
					d3.select("#text_component_{0}_1")
						.append("p")
						.attr("class", "component_text");

					d3.select("#text_component_{0}_1").select(".component_text")
					  .append("text")
					  .attr("dx", "0em")
					  .attr("dy", "0em")
						.append("tspan")
						  .style("font-weight", 700)
						  .text(d3.format(",.0f")(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["_total"])[0]))
						.append("tspan")
						  .style("font-weight", 400)
						  .text(" learners have completed an attempt of the Simulation.");
					*/



					/*if(d3.max(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["_tot"]))) > 0){{*/

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_polar(
						  data=data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"_avg", ci:{{lower:null, upper:null}}}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{
							var:null,
							palette:'dark24', // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
							value:null
						  }}, // Variable containing color of points/lines
						  line={{width:2, opacity:1.0}}, // Values of width and opacity of lines

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true}},
						  group={{var:selected_filter, label:{{value:selected_filter + ":", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true}},
						  switcher={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:selected_filter, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"_avg", format:',.1f', prefix:null, suffix:"%"}}]}}
						  ],

						  xaxis={{
							range:[0, 100],
							suffix:null,
							format:",.0f",
							tick:{{size:10, weight:400}},
							show:true,
							num_ticks:6
						  }},

						  yaxis={{
							height:400,
							offset:{{top:10, bottom:10}},
							tick:{{size:14, weight:400, width:200}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					/*}}*/


					'''.format(key2, proj_selector)


				if key2 == 'dmg_decision_levels':
					html_page += '''
					// DEMOGRAPHICS - DECISION LEVEL SUMMARY

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();



					// --- First Text Grid Element --->

					if( Array.from(new Set(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["coaching"]))).some(element => element != "-") ){{
						  var tooltipText = [
							  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
							  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
							  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:null, format:null, prefix:"Coaching:", suffix:null}}]}},
							  {{size:13, weight:400, text:[{{var:"coaching", format:null, prefix:null, suffix:null}}]}},
							  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"_pct", format:",.1f", prefix:null, suffix:"%"}}]}},
							  {{size:12, weight:400, text:[
								{{var:"_n", format:",.0f", prefix:"(", suffix:" out of "}},
								{{var:"_denom", format:",.0f", prefix:null, suffix:" Learners)"}},
							  ]}}
						  ];
					}}
					else if( Array.from(new Set(data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value).map(d => d["feedback"]))).some(element => element != "-") ){{
						  var tooltipText = [
							  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
							  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
							  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:null, format:null, prefix:"Feedback:", suffix:null}}]}},
							  {{size:13, weight:400, text:[{{var:"feedback", format:null, prefix:null, suffix:null}}]}},
							  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"_pct", format:",.1f", prefix:null, suffix:"%"}}]}},
							  {{size:12, weight:400, text:[
								{{var:"_n", format:",.0f", prefix:"(", suffix:" out of "}},
								{{var:"_denom", format:",.0f", prefix:null, suffix:" Learners)"}},
							  ]}}
						  ];
					}}
					else{{
						  var tooltipText = [
							  {{size:14, weight:700, text:[{{var:"decisiontype", format:null, prefix:null, suffix:":"}}]}},
							  {{size:13, weight:400, text:[{{var:"choice", format:null, prefix:null, suffix:null}}]}},
							  {{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"attempt", format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:700, text:[{{var:"_pct", format:",.1f", prefix:null, suffix:"%"}}]}},
							  {{size:12, weight:400, text:[
								{{var:"_n", format:",.0f", prefix:"(", suffix:" out of "}},
								{{var:"_denom", format:",.0f", prefix:null, suffix:" Learners)"}},
							  ]}}
						  ];
					}}


					var denom = groupAndSum(data_component_dmg["{0}"]["dataSummary"], [selected_filter, "simname", "attempt", "decision_level_num"], ["_n"]);

					data_component_dmg["{0}"]["dataSummary"].forEach(function(vObs, iObs){{

						var this_denom = denom.filter(d => d[selected_filter] == vObs[selected_filter] && d["simname"] == vObs["simname"] && d["attempt"] == vObs["attempt"] && d["decision_level_num"]).map(d => d["_n"])[0]

						vObs['_denom'] = this_denom;
						vObs['_pct'] = (vObs['_n']/vObs['_denom'])*100
					}})

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
					chart_bar_horizontal(
						data=data_component_dmg["{0}"]["dataSummary"].filter(d => {1} d["simname"] == simSelector.value),
						html_id="#chart_component_{0}_1",

						x={{var:"_pct", ascending:true, ci:[null, null]}}, // Must be numeric
						y={{var:selected_filter, order:"as_appear", ascending:true, highlight:null }}, // Must be categorical

						title={{value:null, line:false}},

						clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						facet={{var:null, size:16, weight:700, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:'#d3d2d2'}}}},
						group={{var:"decisiontype", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"decision_ord", ascending:true, show:true}},
						switcher={{var:"attempt", label:{{value:null, size:18, weight:700}}, size:14, weight:700, order:"as_appear", ascending:true, line:false}},
						scroll={{var:"decision_level_basic", label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						bar={{
						  size:14, weight:400,
						  text:[{{var:"_pct", format:",.1f", prefix:null, suffix:"%"}}],
						  extra_height:0,
						  space_between:5,
						  var:null
						}},

						tooltip_text=tooltipText,

						barmode="stack", // "group", "overlay" or "stack"

						column_data={{
						  before_x:null,
						  after_x:null
						}},

						vline={{
						  var:null,
						  value:null
						}},

						xaxis={{
						  range:[0, 100],
						  rangeScroll:"fixed", // "fixed" or "free"
						  rangeFacet:"fixed", // "fixed" or "free"
						  format:",.0f",
						  suffix:"%",
						  tick:{{size:10, weight:400, orientation:'h', splitWidth:150}},
						  label:{{value:null, size:14, weight:700}},
						  offset:{{left:10, right:10}},
						  show:false,
						  show_line:false,
						  show_ticks:true,
						  num_ticks:6,
						  show_grid:true
						}},

						yaxis={{
						  widthPct:{{value:0.4, range:'free', cutText:false}},
						  rangeScroll:"fixed", // "fixed" or "free"
						  rangeFacet:"free", // "fixed" or "free"
						  tick:{{size:14, weight:400}},
						  label:{{value:selected_filter, size:14, weight:700}},
						  offset:{{top:0, bottom:10}},
						  show:true,
						  show_line:false,
						  show_ticks:false,
						}},

						font={{family:body_font}},

						margin={{top:10, bottom:10, left:10, right:10, g:10}},

						canvas={{width:1000}},

						zoom=false
					  );



					'''.format(key2, proj_selector)






				if key2 == 'dmg_learner_counts':

					html_page += '''
					// LEARNER COUNTS BY DEMOGRAPHIC

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(d3.max(data_component_{0}.filter(d => {1} d["simname"] == simSelector.value && d["demog_var"] == demogSelector.value).map(d => d["total"])) > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["simname"] == simSelector.value && d["demog_var"] == demogSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"n", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"demog_val", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:null, palette:"dark24", value:"#1f77b4"}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:"demog_val", label:{{value:null, size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:false}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:12, weight:400,
							text:[
								{{var:"n", format:",.0f", prefix:null, suffix:null}},
								{{var:"pct", format:",.1f", prefix:"(", suffix:"%)"}},
							],
							extra_height:0,
							space_between:5
						  }},

						  tooltip_text=[
							{{size:14, weight:700, text:[{{var:"demog_val", format:null, prefix:null, suffix:null}}]}},
							{{size:12, weight:700, text:[{{var:"n", format:".0f", prefix:null, suffix:" Learners"}}]}},
							{{size:12, weight:400, text:[{{var:"pct", format:",.0f", prefix:"(", suffix:" %)"}}]}}
						  ],

						  barmode="overlay", // "group", "stack" or "overlay"

						  column_data={{
							before_x:null,
							after_x:null
						  }},

						  vline={{
							var:null,
							value:null
						  }},

						  xaxis={{
							range:[0, null],
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							format:",.0f",
							suffix:null,
							tick:{{size:10, weight:400, orientation:"h", splitWidth:150}},
							label:{{value:"Number of Learners", size:12, weight:700}},
							offset:{{left:10, right:10}},
							show:true,
							show_line:false,
							show_ticks:true,
							num_ticks:7,
							show_grid:true
						  }},

						  yaxis={{
							widthPct:{{value:0.4, range:"free"}},
							rangeScroll:"fixed", // "fixed" or "free"
							rangeFacet:"fixed", // "fixed" or "free"
							tick:{{size:12, weight:700}},
							label:{{value:demogSelector.value, size:14, weight:700}},
							offset:{{top:0, bottom:10}},
							show:true,
							show_line:false,
							show_ticks:false,
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, proj_selector)





				if key2 == 'dmg_skill':

					html_page += '''
					// SKILL PERFORMANCE BY DEMOGRAPHIC

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} d["simname"] == simSelector.value && d["demog_var"] == demogSelector.value).length > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_polar(
						  data=data_component_{0}.filter(d => {1} d["simname"] == simSelector.value && d["demog_var"] == demogSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"est", ci:{{lower:"ci_l", upper:"ci_u"}}}}, // Must be numeric
						  y={{var:"skillname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{
							var:null,
							palette:'dark24', // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
							value:null
						  }}, // Variable containing color of points/lines
						  line={{width:2, opacity:1.0}}, // Values of width and opacity of lines

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true}},
						  group={{var:"demog_val", label:{{value:demogSelector.value + ":", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"demog_val", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"est", format:',.1f', prefix:null, suffix:"%"}}]}}
						  ],

						  xaxis={{
							range:[0, 100],
							suffix:null,
							format:",.0f",
							tick:{{size:10, weight:400}},
							show:true,
							num_ticks:6
						  }},

						  yaxis={{
							height:400,
							offset:{{top:10, bottom:10}},
							tick:{{size:14, weight:400, width:200}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, proj_selector)





				if key2 == 'dmg_shared_skill':

					html_page += '''
					// PERFORMANCE IN SHARED SKILLS ACROSS SIMS BY DEMOGRAPHIC

					d3.select("#contentsub_{0}").remove();

					// --- 2x1 Grid --->
					d3.select("#component_content_{0}") //d3.select("#component_content_{0}_collapsible")
					  .append("div")
					  .attr("id", "contentsub_{0}")
					  .style("display", "grid")
					  .style("grid-template-rows", "min-content min-content")
					  .style("grid-template-columns", "1fr")
					  .style("grid-gap", "5px");

					d3.select("#contentsub_{0}").append("div").attr("id", "text_component_{0}_1").style("align-self", "end");
					d3.select("#contentsub_{0}").append("div").attr("id", "chart_component_{0}_1").style("align-self", "start");

					d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();


					if(data_component_{0}.filter(d => {1} d["simname"] == simSelector.value && d["demog_var"] == demogSelector.value).length > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_polar(
						  data=data_component_{0}.filter(d => d["demog_var"] == demogSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"est", ci:{{lower:"ci_l", upper:"ci_u"}}}}, // Must be numeric
						  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:true}},

						  clr={{
							var:null,
							palette:'dark24', // "plotly", "d3", "g10", "t10", "alphabet", "dark24", "light24", "set1", "pastel1"
							value:null
						  }}, // Variable containing color of points/lines
						  line={{width:2, opacity:1.0}}, // Values of width and opacity of lines

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true}},
						  group={{var:"demog_val", label:{{value:demogSelector.value + ":", size:14, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:"skillname", label:{{value:"Skill:", size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:true}},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"skillname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:400, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"demog_val", format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:400, text:[{{var:"est", format:',.1f', prefix:null, suffix:"%"}}]}}
						  ],

						  xaxis={{
							range:[0, 100],
							suffix:null,
							format:",.0f",
							tick:{{size:10, weight:400}},
							show:true,
							num_ticks:6
						  }},

						  yaxis={{
							height:400,
							offset:{{top:10, bottom:10}},
							tick:{{size:14, weight:400, width:200}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:1000}},

						  zoom=false
						);

					}}

					'''.format(key2, proj_selector)





			# Close updateGraph function
			html_page += '''
				}}

				// Adjust heights of collapsible content
				var coll = document.querySelectorAll("#component_content_{0} .collapsible");
				for (let i = 0; i < coll.length; i++) {{
				  var content = coll[i].nextElementSibling;
				  if (content.style.maxHeight){{
					content.style.maxHeight = content.scrollHeight + "px";
				  }}
				}}

			}}

			'''.format(key1)


	html_page += '''

	// Function to assign "options" to drop-down menu
	function assignOptions(textArray, selector) {

	  if(selector.length > 0){
		// Remove optgroups
		//var selectedOptgroup = document.getElementById(selector.getAttribute('id') + '_Diagnostic_Sims');
		//selectedOptgroup.remove();

		//var selectedOptgroup = document.getElementById(selector.getAttribute('id') + '_Developmental_Sims');
		//selectedOptgroup.remove();

				var selectedOptgroup = document.getElementById('Sims_Group');
		selectedOptgroup.remove();

		// Remove options
		var i, L = selector.options.length - 1;
		for(i = L; i >= 0; i--) {
		  selector.remove(i);
		}
	  }

	  // Add option group
	  var currentOptGroup = document.createElement('optgroup');
	  currentOptGroup.id = 'Sims_Group';
	  currentOptGroup.label = 'Simulation'
	  selector.appendChild(currentOptGroup);

	  // Add optgroups and options
	  textArray.forEach(function(v, i){
		//var currentOptGroup = document.createElement('optgroup');
		//currentOptGroup.label = 'Sims' // (i == 0)?'Diagnostic Sims':'Developmental Sims';
		//currentOptGroup.id = 'Sims' //(i == 0)?selector.getAttribute('id') + '_Diagnostic_Sims':selector.getAttribute('id') + '_Developmental_Sims';
		//selector.appendChild(currentOptGroup);


		var currentOption = document.createElement('option');
		currentOption.text = v;
		currentOptGroup.appendChild(currentOption);

		//v.forEach(function(vEntry, vI){
		//    var currentOption = document.createElement('option');
		//    currentOption.text = vEntry;
		//    selector.appendChild(currentOption);
		//})
	  })

	}

	'''



	# Change Graphs when Demographic variable/value changes
	if demog_filters is not None:
		html_page += '''
		demogvarSelector.addEventListener('change', function(){
			// Change options in Demog Value selector
			assignOptions(demogs.filter(d => d['demog_var'] == demogvarSelector.value ).map(d => d['demog_val']), demogvalSelector);

		'''

		if len(dict_df['proj']) > 0:
			html_page += '''
			updateGraphs_proj();
		'''

		if len(dict_df['sim']) > 0:
			html_page += '''
			updateGraphs_sim();
		'''

		if len(dict_df['srv']) > 0:
			html_page += '''
			updateGraphs_srv();
		'''

		html_page += '''
		}, true);

		'''


		html_page += '''
		demogvalSelector.addEventListener('change', function(){
		'''

		if len(dict_df['proj']) > 0:
			html_page += '''
			updateGraphs_proj();
		'''

		if len(dict_df['sim']) > 0:
			html_page += '''
			updateGraphs_sim();
		'''

		if len(dict_df['srv']) > 0:
			html_page += '''
			updateGraphs_srv();
		'''

		html_page += '''
		}, true);

		'''



	# Change graphs when projSelector changes
	if len(dict_df['proj']) > 0:
		html_page += '''
		// Update plots when dropdown selections change
		projSelector.addEventListener('change', function(){
			var proj_sims = Array.from(new Set(data_component_proj_sims.filter(d => d['project'] == projSelector.value ).map(d => d['simname'])));

			d3.select("#sim_header_proj").selectAll("tspan").remove();
			proj_sims.forEach(function(vSim, iSim, aSim){
			  d3.select("#sim_header_proj")
				.append("tspan")
				  .style("font-weight", "normal")
				  .text(vSim);
			});

			assignOptions(proj_sims, simSelector);

			updateGraphs_proj();

			// Update Plotly Express chart visibility
			if (typeof updateProjEngagementChart === 'function') {
				updateProjEngagementChart();
			}
		'''

		if len(dict_df['sim']) > 0:
			html_page += '''
			updateGraphs_sim();
		'''

		if len(dict_df['srv']) > 0:
			html_page += '''
			updateGraphs_srv();
		'''

		if len(dict_df['dmg']) > 0:
			html_page += '''
			updateGraphs_dmg();
		'''

		html_page += '''
		}, true);
		'''


	# Change graphs when simSelector changes
	html_page += '''
	simSelector.addEventListener('change', function(){
		d3.select("#sim_header").text(simSelector.value);

	'''

	if len(dict_df['sim']) > 0:
		html_page += '''
		updateGraphs_sim();
		'''

	if len(dict_df['srv']) > 0:
		html_page += '''
		updateGraphs_srv();
		'''

	if len(dict_df['dmg']) > 0:
		html_page += '''
		updateGraphs_dmg();
		'''

	html_page += '''

	}, true);
	'''



	# Change graphs when demogSelector changes
	"""
	if len(dict_df['dmg']) > 0:
		html_page += '''
		// Update plots when dropdown selections change
		demogSelector.addEventListener('change', function(){

			updateGraphs_dmg();
		'''

		html_page += '''
		}, true);
		'''
	"""




	if len(dict_df['proj']) > 0:
		html_page += '''
		/* ----- Create initial version of graphs ----> */
		assignOptions(Array.from(new Set(data_component_sims.filter(d => d['project'] == projSelector.value ).map(d => d['simname']))), simSelector);
		'''
	else:
		html_page += '''
		/* ----- Create initial version of graphs ----> */
		assignOptions(sims, simSelector);
		'''

	if len(dict_df['proj']) > 0:
		html_page += '''
		d3.select("#sim_header_proj").selectAll(".tspan").remove();
		Array.from(new Set(data_component_proj_sims.filter(d => d['project'] == projSelector.value ).map(d => d['simname']))).forEach(function(vSim, iSim, aSim){
		  d3.select("#sim_header_proj")
			.append("tspan")
			  .style("font-weight", "normal")
			  .text(vSim);
		});

		'''

	html_page += '''
	d3.select("#sim_header").text(simSelector.value);

	'''

	for key in dict_df:
		if len(dict_df[key]) > 0:

			updateFunction = 'createSummaryData();' if key == "dmg" else "updateGraphs_{0}();".format(key)

			html_page += '''
			{0}
			'''.format(updateFunction)


	html_page += '''


	// ----- Collapsing Sections ----->
	var coll = document.getElementsByClassName("collapsible");
	var i;

	for (i = 0; i < coll.length; i++) {
	  coll[i].addEventListener("click", function() {
		this.classList.toggle("collapse_active");
		var content = this.nextElementSibling;
		//console.log('# content.style.maxHeight:', content.style.maxHeight, '# content.scrollHeight:', content.scrollHeight)
		if (content.style.maxHeight){
		  content.style.maxHeight = null;
		} else {
		  content.style.maxHeight = content.scrollHeight + "px";
		}
	  });

	  // Initialize with all content showing
	  var content = coll[i].nextElementSibling;
	  content.style.maxHeight = content.scrollHeight + "px";
	}



	// ----- LEFT-MENU: Add hovered class in selected list item ---->
	let list = document.querySelectorAll('.as_navigation li');
	function activeLink(){
		if(!Array.from(this.classList).includes("toggle")){
			list.forEach((item) =>
			item.classList.remove('hovered'));
			this.classList.add('hovered');
				//this.style = "background-color: #efefef !important;";
		}
	}
	list.forEach((item) =>
	item.addEventListener('click', activeLink));

	openTab(event, list[2].id + "_data")


	/*
	list.forEach(function(vItem, iItem){
		if(iItem > 0){
			vItem.click();
			console.log('vItem.id:', vItem.id)

			var theseButtons = document.querySelectorAll("#component_content_" + vItem.id + " .rowdivider .collapsible");
			console.log('theseButtons:', theseButtons);
			for (let j = 0; j < theseButtons.length; j++){
				theseButtons[j].click();
			}
		}
	});
	list[2].click();
	*/

	/* <----- Add hovered class in selected list item ----- */


	'''


	html_page += '''
		//]]>
		</script>
		</div>
		</main>
	<footer class="footer">
		<h2 id="footerelem" class="copyright">© 2025 Skillwell. All rights reserved. Access is granted to authorized users only.</h2>
	</footer>
	</div>
	
	</body>
	</html>
	'''

	return html_page