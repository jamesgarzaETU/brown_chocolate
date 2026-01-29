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
import json
from datetime import date, timedelta, datetime
import time
import html
import re
import xml.etree.ElementTree as ET
import unicodedata
import math
import os
import shutil
from subprocess import call
import json


port = 7737

# ------------------------------------------------------------------------------------>
# ----- Function to find EC2 ID using customer name (eg. "client.skillsims.com") ----->
# ------------------------------------------------------------------------------------>

def find_ec2(customer_name):
	"""
	Finds the EC2 instance running in the specified regions ('us-east-1', 'eu-west-1')
	that has a tag with the key 'serverName' and a value matching the provided customer name.

	Args:
		customer_name (str): The name of the customer to search for in the 'serverName' tag.

	Returns:
		tuple: A tuple containing the instance ID and region of the matching EC2 instance. 
			   Returns None if no instance is found.
			   Example: ('i-1234567890abcdef0', 'us-east-1')

	Example:
		ec2_id, region = find_ec2("customerA")
		print(f"EC2 Instance ID: {ec2_id}, Region: {region}")

	"""
	# Iterate over a list of two AWS regions: 'us-east-1' and 'eu-west-1'
	for region in ['us-east-1', 'eu-west-1']:
		
		# Create an EC2 resource object for the current region
		ec2 = boto3.resource('ec2', region_name=region)
		
		# Iterate through all EC2 instances in the current region
		for instance in ec2.instances.all():
			
			# Check if the instance is in the 'running' state and has tags
			if instance.state['Name'] == "running" and instance.tags is not None:
				
				# Iterate through the tags of the instance to find the specific 'serverName' tag
				for tag in instance.tags:
					
					# If the tag key is 'serverName' and its value matches the given 'customer_name'
					if tag.get('Key') == 'serverName' and tag.get('Value') == customer_name:
						
						# Store the instance ID of the matching instance
						ec2_id = instance.instance_id
						
						# Delete the EC2 resource object to free up resources
						del ec2
						
						# Return the EC2 instance ID and region where the instance is located
						return ec2_id, region

		# Delete the EC2 resource object to release resources after processing the region
		del ec2
	
	# Return None if no matching instance was found
	return None

# ------------------------------------------------------------------------------------------------->
#  Function to find Aurora Cluster or RDS ID using customer name (eg. "client.skillsims.com") ----->
# ------------------------------------------------------------------------------------------------->

def find_rds(customer_name):
    """
    Finds an Aurora Cluster or RDS Instance for the given customer.
    
    Returns:
        tuple: (rds_id, rds_port, region)
    """
    
    # 1. Prepare identifier for Aurora search
    customer_short_name = customer_name.split('.')[0]
    expected_cluster_id = f"{customer_short_name}-aurora-cluster"

    for region in ['us-east-1', 'eu-west-1']:
        
        # -----------------------------------------------------------
        # A. Try to find Aurora Cluster first
        # -----------------------------------------------------------
        try:
            rds = boto3.client('rds', region_name=region)
            
            paginator = rds.get_paginator('describe_db_clusters').paginate()
            for page in paginator:
                for dbcluster in page['DBClusters']:
                    # Check if Cluster Identifier matches
                    if dbcluster['DBClusterIdentifier'] == expected_cluster_id:
                        
                        # Use Reader Endpoint if available, else Writer Endpoint
                        rds_id = dbcluster.get('ReaderEndpoint') or dbcluster.get('Endpoint')
                        # Extract Port (Aurora Clusters have Port at the top level)
                        rds_port = dbcluster.get('Port')
                        
                        rds.close()
                        del rds
                        
                        return rds_id, rds_port, region

        except Exception as e:
            print(f"Error searching for cluster in {region}: {e}")
            # Continue to check instances in this region if cluster fails
            pass 

        # -----------------------------------------------------------
        # B. Fallback: Try to find Standard RDS Instance via Tags
        # -----------------------------------------------------------
        try:
            # Re-instantiate client if the previous block closed it or failed
            # (In a clean flow, we could reuse the client, but keeping your structure safe)
            rds = boto3.client('rds', region_name=region)
            
            paginator = rds.get_paginator('describe_db_instances').paginate()
            for page in paginator:
                for dbinstance in page['DBInstances']:
                    for tag in dbinstance.get('TagList', []):
                        if tag.get('Value') == customer_name:
                            
                            # Extract Address and Port from Endpoint dict
                            rds_id = dbinstance['Endpoint']['Address']
                            rds_port = dbinstance['Endpoint']['Port']
                            
                            rds.close()
                            del rds
                            
                            return rds_id, rds_port, region
            
            # Clean up if loop finishes without finding anything in this region
            rds.close()
            del rds

        except Exception as e:
             # Log error but continue to next region
             print(f"Error searching for instance in {region}: {e}")
             pass

    # -----------------------------------------------------------
    # C. If nothing found after checking all regions
    # -----------------------------------------------------------
    error_message = {
        'errorType': 'RDS_Error',
        'errorMessage': 'Unable to find RDS Database (Aurora Cluster "{0}" or Instance tagged "{1}")'.format(expected_cluster_id, customer_name),
        'errorFunction': 'AutoInsights_GetReportParameter'
    }
    raise Exception(str(error_message))


# ------------------------------------------------------------------------------------>
# ----- Function to find S3 Bucket using customer name (eg. "client.skillsims.com") ----->
# ------------------------------------------------------------------------------------>

def find_s3(customer_name):
	"""
	Finds the S3 bucket in the specified regions ('us-east-1', 'eu-west-1')
	that contains 'etu.' in its name and where the customer name (before the first dot)
	matches the second part of the bucket name.

	Args:
		customer_name (str): The customer name to search for in the S3 bucket name.

	Returns:
		tuple: A tuple containing the S3 bucket name and its region. 
			   Returns None if no matching S3 bucket is found.
			   Example: ('etu.customerA.bucket', 'us-east-1')

	Example:
		s3_id, s3_region = find_s3("customerA.something")
		print(f"S3 Bucket Name: {s3_id}, Region: {s3_region}")

	"""
	# Iterate over a list of two AWS regions: 'us-east-1' and 'eu-west-1'
	for region in ['us-east-1', 'eu-west-1']:
		
		# Create an S3 client object for the current region
		s3 = boto3.client('s3', region_name=region)
		
		# Iterate through all the S3 buckets in the current region
		for bucket in s3.list_buckets()['Buckets']:
			
			# Check if the bucket name contains 'etu.' and if the customer name matches
			if 'etu.' in bucket['Name'] and customer_name.split('.')[0] == bucket['Name'].split('.')[1]:
				
				# Store the bucket name as the S3 ID
				s3_id = bucket['Name']

				# Get the location of the S3 bucket to find its region
				response = s3.get_bucket_location(Bucket=s3_id)
				s3_region = response['LocationConstraint']

				# Close the S3 client connection and delete the object
				s3.close()
				del s3
				
				# Return the S3 bucket name and region
				return s3_id, s3_region

		# Close the S3 client connection and delete the object after processing the region
		s3.close()
		del s3
	
	# Return None if no matching S3 bucket is found
	return None

# -------------------------------------------------------->
# ----- Get list of AWS resources (EC2, RDS and S3) ----->
# -------------------------------------------------------->

def aws_resources():
	"""
	Retrieves information about running AWS resources (EC2, RDS, and S3) in the specified regions ('us-east-1', 'eu-west-1')
	and returns a merged DataFrame containing details of these resources for each client.

	The function collects the following data:
	- EC2: Instance ID, state, and client name from EC2 instances with the 'serverName' tag.
	- RDS: Endpoint address, port, and client name from RDS instances with the 'serverName' tag.
	- S3: Bucket name and client name from S3 buckets that contain 'etu.' in their name.

	Data from EC2, RDS, and S3 is merged by client and region, with additional processing for RDS endpoint and port.
	The final DataFrame includes only running EC2 instances.

	Returns:
		pandas.DataFrame: A DataFrame containing details of the AWS resources for each client.
						   The DataFrame contains columns for client, region, EC2 instance ID, state, RDS endpoint, RDS port, and S3 bucket.
	
	Example:
		df_aws = aws_resources()
		print(df_aws)

	"""
	# Lists to store EC2, RDS, and S3 resource data
	list_aws_ec2 = []
	list_aws_rds = []
	list_aws_s3 = []

	# Iterate over the list of AWS regions
	for region in ['us-east-1', 'eu-west-1']:

		# --- All EC2 --->
		ec2 = boto3.resource('ec2', region_name=region)

		for instance in ec2.instances.all():
			dict_aws_ec2 = {}

			if instance.tags is not None:
				for tag in instance.tags:
					if tag.get('Key') == 'serverName':
						dict_aws_ec2.update({
							'client': tag.get('Value'),
							'region': region,
							'ec2_id': instance.instance_id,
							'state': instance.state['Name']
						})

				list_aws_ec2.append(dict_aws_ec2)

		df_aws_ec2 = pd.DataFrame.from_records(list_aws_ec2)
		del ec2
		# <--- All EC2 ---



		# --- All RDS --->
		rds = boto3.client('rds', region_name=region)

		paginator = rds.get_paginator('describe_db_instances').paginate()
		for page in paginator:
			for dbinstance in page['DBInstances']:
				for tag in dbinstance['TagList']:
					if tag.get('Key') == 'serverName':
						list_aws_rds.append({
							'client': tag.get('Value'),
							'region': region,
							'rds_endpoint': dbinstance['Endpoint']['Address'],
							'rds_port': dbinstance['Endpoint']['Port'],
						})

		rds.close()
		del rds

		df_aws_rds = pd.DataFrame.from_records(list_aws_rds)
		# <--- All RDS ---



		# --- All S3 Buckets --->
		s3 = boto3.client('s3', region_name=region)

		for bucket in s3.list_buckets()['Buckets']:
			if 'etu.' in bucket['Name']:
				list_aws_s3.append({
					'client': bucket['Name'][bucket['Name'].find('.') + 1:] + '.skillsims.com',
					'region': region,
					's3_bucket': bucket['Name']
				})

		s3.close()
		del s3

		df_aws_s3 = pd.DataFrame.from_records(list_aws_s3)
		# <--- All S3 Buckets --->

	# Merging EC2, RDS, and S3 data based on client and region
	df_aws = df_aws_ec2 \
		.merge(df_aws_rds, how='outer', on=['client', 'region']) \
		.merge(df_aws_s3, how='left', on=['client', 'region']) \
		.assign(
			rds_endpoint=lambda x: x['rds_endpoint'].apply(lambda y: '127.0.0.1' if pd.isnull(y) else y),
			rds_port=lambda x: x['rds_port'].apply(lambda y: int(3306) if pd.isnull(y) else int(y)),
		) \
		.query('state == "running"')

	return df_aws


# -------------------------------------------------->
# ----- Function to create and open SSH Tunnel ----->
# -------------------------------------------------->

def sshtunnel(
	servername,
	credentials,
	remote_address='127.0.0.1',
	remote_port=3306,
	local_port=3307):
	"""
	Establishes an SSH tunnel to a remote server and forwards traffic from a local port to a remote port.

	Args:
		servername (str): The address or hostname of the remote SSH server.
		credentials (dict): A dictionary containing SSH credentials. Expected keys are:
			- 'ssh_username': The username for SSH authentication.
			- 'ssh_password': The password for SSH authentication (optional if using 'ssh_pkey').
			- 'ssh_pkey': The private key for SSH authentication (optional if using 'ssh_password').
		remote_address (str, optional): The remote server's address to bind to. Defaults to '127.0.0.1'.
		remote_port (int, optional): The remote port to forward to. Defaults to 3306 (typically used for MySQL).
		local_port (int, optional): The local port to bind for the tunnel. Defaults to 3307.

	Returns:
		SSHTunnelForwarder: An active SSH tunnel that can be used to forward traffic between local and remote ports.
		
	Example:
		credentials = {
			'ssh_username': 'myuser',
			'ssh_password': 'mypassword',
			'ssh_pkey': '/path/to/private/key'
		}
		tunnel = sshtunnel('my.remote.server.com', credentials)
		print(f"SSH Tunnel started on local port {tunnel.local_bind_port}")

	"""
	# Create and start the SSH tunnel
	tunnel = SSHTunnelForwarder(
		servername,
		ssh_username         =   credentials['ssh_username'],
		ssh_password         =   credentials.get('ssh_password'),
		ssh_pkey             =   credentials.get('ssh_pkey'),
		remote_bind_address  =   (remote_address, remote_port),
		local_bind_address   =   ('127.0.0.1', local_port)
	)

	# Start the tunnel
	tunnel.start()
	
	# Return the tunnel object for further interaction
	return tunnel

# -------------------------------------------------------------->
# ----- Function to connect to Client Server using pymysql ----->
# -------------------------------------------------------------->

def dbconnect(tunnel, credentials):
	"""
	Establishes a connection to a MySQL database using a forwarded SSH tunnel.

	Args:
		tunnel (SSHTunnelForwarder): An active SSH tunnel object that forwards traffic from the local port to the remote MySQL server.
		credentials (dict): A dictionary containing MySQL credentials. The dictionary is expected to include:
			- 'user': The MySQL username for authentication.
			- 'password': The MySQL password for authentication.
			- 'database': The name of the MySQL database to connect to.

	Returns:
		pymysql.connections.Connection: A connection object to the MySQL database, which can be used to execute queries.

	Example:
		tunnel = sshtunnel('my.remote.server.com', credentials)
		db = dbconnect(tunnel, credentials)
		print("Connected to the database!")

	"""
	# Establishing a connection to the MySQL database via the SSH tunnel
	db = pymysql.connect(
		#user='etu_data',  # MySQL username, typically 'root' for administrative access
		user='root',  # MySQL username, typically 'root' for administrative access
		password='assf1r3mysql',  # MySQL password for the 'root' user
		host=tunnel.local_bind_host,  # The local host forwarded by the SSH tunnel
		port=tunnel.local_bind_port,  # The local port forwarded by the SSH tunnel
		database='etu_sim'  # The MySQL database to connect to
	)

	return db

# --------------------------------------------------------------->
# ----- Function to connect to Client Server using Paramiko ----->
# --------------------------------------------------------------->

def client_connect(
	hostname,
	region="us-east-1",  # Region where the client server is located (eu-west-1 or us-east-1)
	config_file_dir="/home/ubuntu/.ssh"): # Location on local machine where regional SSH configuration files are located
	"""
	Establishes an SSH connection to a client EC2 server in a specified AWS region.

	Args:
		hostname (str): The AWS EC2 instance ID or hostname of the target client server (e.g., 'i-04996b8f051b68354').
		
		region (str, optional): The AWS region where the client server is located (either 'eu-west-1' or 'us-east-1').
			Defaults to 'us-east-1'.
		
		config_file_dir (str, optional): The location on the local machine where the SSH region configuration files
			(for 'eu-west-1' and 'us-east-1') are stored. Defaults to '/home/ubuntu/.ssh'.

	Returns:
		paramiko.SSHClient: An SSH client object connected to the specified client server.
		
	Example:
		client = client_connect('i-04996b8f051b68354', region='us-east-1')
		print("SSH connection established!")

	"""
	# Create the SSH client instance
	client = paramiko.SSHClient()

	# Load the SSH configuration from the specified region's config file
	config = paramiko.SSHConfig.from_file(open(config_file_dir + "/" + region))
	
	# Set the policy to automatically add the server's host key to known hosts
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

	# Retrieve the SSH configuration for the specific host (EC2 ID or hostname)
	ssh_config = config.lookup(hostname)

	# Setup a proxy command if specified in the SSH config
	sock = paramiko.proxy.ProxyCommand(ssh_config.get("proxycommand"))

	# Connect to the target server using SSH with the provided credentials and proxy setup
	client.connect(
		hostname=hostname,
		key_filename=credentials["ssh_pkey"],
		username=credentials["ssh_username"],
		sock=sock
	)

	# Return the connected SSH client object
	return client

# <-----------------------------------------------------
# <----- Function to download xml file from server -----
# <-----------------------------------------------------

def download_xml(
	ec2_id,
	filename,
	localdir='/home/ubuntu',
	config_file_dir="/home/ubuntu/.ssh", # location of ssh region configuration files
	region="us-east-1" # eu-west-1 or us-east-1
	):
	"""
	Downloads XML files from a remote EC2 server to the local machine using SFTP over an SSH connection.

	Parameters
	----------
	ec2_id : str
		AWS EC2 ID of the client server to target (e.g., 'i-04996b8f051b68354' for amazon.skillsims.com).

	filename : str or list of str
		Name(s) of the file(s) to download (e.g., 'Sim42/Sim20.20.xml' or 
		['Sim42/Sim20.20.xml', 'Sim76/Sim76.10.xml']).

	localdir : str, optional
		Directory on the local machine where the file(s) will be saved. Defaults to '/home/ubuntu'.

	config_file_dir : str, optional
		Location on the local machine where regional SSH configuration files (for 'eu-west-1' and 'us-east-1')
		are located. Defaults to '/home/ubuntu/.ssh'.

	region : str, optional
		AWS region where the client server is located. Must be either 'eu-west-1' or 'us-east-1'. Defaults to 'us-east-1'.

	"""
	
	hostname = ec2_id  # The hostname is set to the EC2 ID (e.g., 'i-04996b8f051b68354')

	# Create SSH client and load configuration from the given region
	client = paramiko.SSHClient()
	config = paramiko.SSHConfig.from_file(open(config_file_dir + "/" + region))
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh_config = config.lookup(hostname)
	sock = paramiko.proxy.ProxyCommand(ssh_config.get("proxycommand"))

	# Connect to the remote server via SSH using the credentials and proxy command
	client.connect(
		hostname=hostname,
		key_filename=credentials["ssh_pkey"],
		username=credentials["ssh_username"],
		sock=sock
	)

	# Open SFTP session to interact with remote files
	ftp_client = client.open_sftp()

	sourcedir = "/usr/local/etu_sims"

	# If filename is a list, download each file in the list
	if isinstance(filename, list):
		for file in filename:
			# Temporarily change permissions to allow downloading
			client.exec_command(f'sudo find {sourcedir}/{file.split("/")[0]} -type d -exec chmod 777 {{}} +')

			time.sleep(1)  # Wait for permission changes to take effect

			# Transfer the file from the remote server to the local directory
			ftp_client.get(
				remotepath=f"{sourcedir}/{file}",
				localpath=f"{localdir}/{file.split('/')[1]}"
			)

			# Revert the permissions back to the original state
			client.exec_command(f'sudo find {sourcedir}/{file.split("/")[0]} -type d -exec chmod 750 {{}} +')

			print(f"{file.split('/')[1]} download successful")

		# Close the SFTP session and SSH connection
		ftp_client.close()
		client.close()

	else:  # If a single filename is provided
		# Temporarily change permissions to allow downloading
		client.exec_command(f'sudo find {sourcedir}/{filename.split("/")[0]} -type d -exec chmod 777 {{}} +')

		time.sleep(1)  # Wait for permission changes to take effect

		# Transfer the file from the remote server to the local directory
		ftp_client.get(
			remotepath=f"{sourcedir}/{filename}",
			localpath=f"{localdir}/{filename.split('/')[1]}"
		)

		ftp_client.close()  # Close SFTP session

		print(f"{filename.split('/')[1]} download successful")

		# Revert the permissions back to the original state
		client.exec_command(f'sudo find {sourcedir}/{filename.split("/")[0]} -type d -exec chmod 750 {{}} +')

		# Close SSH connection
		client.close()

# <-----------------------------------------------------
# <----- Function to download xml file from server -----
# <-----------------------------------------------------





# ------------------------------------->
# ----- Function to clean strings ----->
# ------------------------------------->

def stringcleaner(x):
	"""
	Cleans a given string by removing carriage return characters, stripping leading and trailing whitespace,
	and ensuring proper encoding and decoding.

	Args:
		x (str): The input string to be cleaned.

	Returns:
		str: The cleaned string after removing carriage return characters, trimming whitespace, and ensuring UTF-8 encoding.

	Example:
		cleaned_string = stringcleaner("  Some text with \r carriage return and extra spaces  ")
		print(cleaned_string)  # Output: "Some text with carriage return and extra spaces"
	"""
	
	# Replace carriage return characters with a space and strip leading/trailing spaces
	clean = x.replace("\r", " ").strip()
	
	# Ensure the string is properly encoded to UTF-8 and then decoded
	clean = clean.encode("utf-8").decode()
	
	return clean

# ----------------------------------------------------------------->
# ----- Function to convert .xml file into a pandas dataframe ----->
# ----------------------------------------------------------------->

def xml_to_df(file, split_score=False):
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
		#result = element.find("./dialog/response").text


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

			if score_ !=None:
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





# ------------------------------------------------------------------------>
# ----- Function to calculate Sim Levels in a Sim using the XML data ----->
# ------------------------------------------------------------------------>

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

	Example:
		df_sim = sim_levels(df)
		print(df_sim.head())
	"""
	# Check if data frame contains the required columns
	if set(['relationid', 'relationtype']).issubset(df.columns):

		### Step 1: Get unique Dialogue IDs
		#print('Step 1: Get unique Dialogue IDs')

		levels0 = df\
		.query('not relationid.str.contains("None")')\
		.assign(
			startingpoint = lambda x: x['relationid'].str.split('-', expand=True)[0].astype(int),
			endpoint = lambda x: x['relationid'].str.split('-', expand=True)[1].astype(int)
		)\
		.filter(['startingpoint', 'endpoint'])\
		.drop_duplicates()



		### Step 2: Find all Dialogue IDs that are Decision Points
		#print('Step 2: Find all Dialogue IDs that are Decision Points')

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
		#print('Step 3: Traverse DOWN, and then back UP the dialogue paths')

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




		### Step 5: Keep results that are common between Steps 1 and 2

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
				#method3 = lambda x: x.apply(lambda y: y['dialogueid'] if pd.isnull(y['method3']) else y['method3'], axis=1),
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



			#if all(levels['method1'] == levels['method2']):
			#    return_cols = ['dialogueid', 'method1']
			#else:
			#    return_cols = ['dialogueid', 'method1', 'method2', 'method3']



			### Step 8: Check for Performance Branches

			if 'performancebranch' in df.columns:

				if df.query('performancebranch == 1').shape[0] > 0:

					#return_cols.append('performancebranch')

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
			#.filter(['end'])\
			#.rename(columns={'end':'start'})

			#print('# start node:')
			#print(df_next)


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

	else:
		print('**ERROR: Data frame does not contain relationid and relationtype')
		return






# ----------------------------------------------------------------->
# ----- Function to create colour scale between 2 RGB colours ----->
# ----------------------------------------------------------------->

def rgb_scale(rgb_from,  # List of the 3 RGB numbers (e.g., [98, 17, 16])
			  rgb_to,    # List of the 3 RGB numbers (e.g., [255, 255, 255])
			  n          # Number of colours to create
			 ):
	"""
	Generates a list of RGB color values that create a gradient from one RGB color to another.

	This function creates a gradient of `n` colors between two given RGB values, `rgb_from` (starting color)
	and `rgb_to` (ending color). The function computes intermediate colors and returns them in a format suitable
	for CSS styling (i.e., 'rgb(R, G, B)').

	Args:
		rgb_from (list of int): A list of 3 integers representing the starting RGB color (e.g., [98, 17, 16]).
		rgb_to (list of int): A list of 3 integers representing the ending RGB color (e.g., [255, 255, 255]).
		n (int): The number of colors to generate in the gradient, including the start and end colors.

	Returns:
		list of str: A list of `n` RGB color strings in the format 'rgb(R, G, B)', representing the colors in the gradient.

	Example:
		gradient = rgb_scale([98, 17, 16], [255, 255, 255], 5)
		print(gradient)  # Output: ['rgb(98,17,16)', 'rgb(136,68,68)', 'rgb(174,119,119)', 'rgb(212,170,170)', 'rgb(255,255,255)']
	"""
	rgb = []

	# Convert input lists to numpy arrays for easier manipulation
	rgb_from = np.array(rgb_from)
	rgb_to = np.array(rgb_to)

	# Calculate the difference between the colors and divide by (n-1) to get the step size
	chg = np.floor((rgb_to - rgb_from) / (n - 1))

	# Generate the intermediate colors
	for i in range(n - 1):
		rgb.append(list((rgb_from + (chg * i)).astype(int)))

	# Add the final color (rgb_to) to the list
	rgb.append(list(rgb_to))

	# Convert the list of RGB colors to 'rgb(R, G, B)' format
	return ['rgb(' + str(x[0]) + ',' + str(x[1]) + ',' + str(x[2]) + ')' for x in rgb]


# -------------------------------------------------------------------->
# ----- Function for extracting raw Sim Data from mySQL database ----->
# -------------------------------------------------------------------->

def extract_raw_data(
	server,
	port=7654,

	simname=None, # List of Sim names
	simid=None,   # List of Sim IDs

	extract_simulation=True,
	extract_score=True,
	extract_section=True,
	extract_user=True,
	extract_user_group=True,
	extract_user_log=False,
	extract_user_sim_log=True,
	extract_sim_score_log=True,
	extract_user_dialogue_log=True,
	extract_dialogue_score_log=False,
	extract_explore_sim_log=False,
	extract_quiz_data=True,
	extract_user_dialogue_rank=False,
	extract_language=True,
	extract_knowledge_check=False,
	):
	"""
	Extracts raw data from a simulation's database and returns it as a dictionary of DataFrames.

	This function connects to an AWS EC2 instance, establishes an SSH tunnel to a MySQL database, and then extracts
	simulation-related data based on the specified flags. The extracted data includes various tables such as simulation
	details, user logs, scores, quiz data, and more, depending on the flags provided.

	Args:
		server (str): The client/server identifier to look up in the AWS resources.
		port (int, optional): The local port for the SSH tunnel. Defaults to 7654.
		simname (list of str, optional): A list of simulation names to filter by.
		simid (list of int, optional): A list of simulation IDs to filter by.
		extract_simulation (bool, optional): Whether to extract data from the 'simulation' table. Defaults to True.
		extract_score (bool, optional): Whether to extract data from the 'score' table. Defaults to True.
		extract_section (bool, optional): Whether to extract data from the 'section' table. Defaults to True.
		extract_user (bool, optional): Whether to extract data from the 'user' table. Defaults to True.
		extract_user_group (bool, optional): Whether to extract data from the 'user_group' table. Defaults to True.
		extract_user_log (bool, optional): Whether to extract data from the 'user_log' table. Defaults to False.
		extract_user_sim_log (bool, optional): Whether to extract data from the 'user_sim_log' table. Defaults to True.
		extract_sim_score_log (bool, optional): Whether to extract data from the 'sim_score_log' table. Defaults to True.
		extract_user_dialogue_log (bool, optional): Whether to extract data from the 'user_dialogue_log' table. Defaults to True.
		extract_dialogue_score_log (bool, optional): Whether to extract data from the 'dialogue_score_log' table. Defaults to False.
		extract_explore_sim_log (bool, optional): Whether to extract data from the 'explore_sim_log' table. Defaults to False.
		extract_quiz_data (bool, optional): Whether to extract quiz data ('quiz_question', 'quiz_answer', 'quiz_option'). Defaults to True.
		extract_user_dialogue_rank (bool, optional): Whether to extract data from the 'user_dialogue_rank' table. Defaults to False.
		extract_language (bool, optional): Whether to extract data from the 'language' table. Defaults to True.
		extract_knowledge_check (bool, optional): Whether to extract knowledge check data ('knowledge_question', 'knowledge_option', 'knowledge_answer'). Defaults to False.

	Returns:
		dict: A dictionary where the keys are table names (e.g., 'simulation', 'score') and the values are DataFrames containing the extracted data.

	Example:
		data = extract_raw_data('my_server', simname=['Sim1', 'Sim2'])
		print(data['simulation'])  # Display the 'simulation' table data
	"""

	# Function for dealing with variables that are 'bits' in MySQL
	def bit_var(x,y):
		if x == 'bit(1)':
			return y + '+0 as ' + y
		else:
			return y




	# List all EC2 and RDS resources on AWS
	if 'df_aws' not in globals():
		df_aws = aws_resources()


	# Kill any process that is using local Port
	os.system('lsof -ti:{0} | xargs kill -9'.format(str(port)))
	call('lsof -ti:{0} | xargs kill -9'.format(str(port)), shell=True)


	# Create SSH Tunnel to client server
	while 'tunnel' not in locals():
		try:
			for ec2_id in df_aws.query('client == @server')['ec2_id'].unique():
				print('ec2_id:', ec2_id)
				try:
					tunnel = sshtunnel(
						ec2_id, #server,
						credentials,
						remote_address=df_aws.query('client == @server')['rds_endpoint'].iloc[0],
						remote_port=int(df_aws.query('client == @server')['rds_port'].iloc[0]),
						local_port=port
					)
					print(server, ': Tunnel open')

					ec2_id_working = ec2_id
					break

				except BaseException as e:
					print('***ERROR***: Cannot connect to EC2 ID:', ec2_id, ':', e)

		except:
			pass


	# Connect to mySql Database on client server
	while 'dbconnection' not in locals():
		try:
			dbconnection = dbconnect(tunnel, credentials)
			print(server, ': Connected to SQL database')

		except:
			pass




	# --- Extract data --->
	try:
		if simid is None or not isinstance(simid, list):
			if simname is None or not isinstance(simname, list):
				simid = pd.read_sql_query("SELECT simid FROM simulation;", dbconnection)
				simid = ', '.join(map(str, simid.iloc[:,0]))
			else:
				simid = pd.read_sql_query("SELECT simid FROM simulation WHERE name IN ({0});".format(', '.join(map(( lambda x: "'" + x + "'"), simname))), dbconnection)
				simid = ', '.join(map(str, simid.iloc[:,0]))

		else:
			simid = ', '.join(map(str, simid))

		print('SIMID =', simid)

	except BaseException as e:
		print('ERROR*** : '+ str(e))


	if simid:

		dict_data = {}

		# 1. Get data from tables that have simid
		tbls = []
		if extract_simulation:
			tbls.append('simulation')
		if extract_score:
			tbls.append('score')
		if extract_section:
			tbls.append('section')
		if extract_user_sim_log:
			tbls.append('user_sim_log')
		if extract_user_dialogue_log:
			tbls.append('user_dialogue_log')
		if extract_sim_score_log:
			tbls.append('sim_score_log')
		if extract_explore_sim_log:
			tbls.append('explore_sim_log')
		if extract_quiz_data:
			tbls.append('quiz_question')
		if extract_knowledge_check:
			tbls.append('knowledge_question')

		if len(tbls) > 0:
			for tbl in tbls:

				try:
					# Get list of columns in table and amend for 'bit' variables
					cols = pd.read_sql_query("SHOW COLUMNS FROM {0};".format(tbl), dbconnection)
					cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))


					dict_data[tbl] = pd.read_sql_query("SELECT {0} FROM {1} WHERE simid in ({2});".format(cols, tbl, simid), dbconnection)
					print("{} extracted".format(tbl))

				except BaseException as e:
					print('ERROR*** : '+ str(e))



		# 2. Get User data
		if extract_user:
			try:
				# Get list of columns in table and amend for 'bit' variables
				cols = pd.read_sql_query("SHOW COLUMNS FROM user;", dbconnection)
				cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

				dict_data['user'] = pd.read_sql_query(
					'''
					SELECT t1.*
					FROM
						(
							SELECT {0}
							FROM user
						) t1
					INNER JOIN
						(
							SELECT DISTINCT userid
							FROM user_sim_log
							WHERE simid in ({1})
						) t2
					ON t1.userid = t2.userid;
					'''.format(cols, simid), dbconnection)

				print("user extracted")


			except BaseException as e:
				print('ERROR*** : '+ str(e))


		# 3. Get User Log data
		if extract_user_log:
			try:
				# Get list of columns in table and amend for 'bit' variables
				cols = pd.read_sql_query("SHOW COLUMNS FROM user_log;", dbconnection)
				cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

				dict_data['user_log'] = pd.read_sql_query(
					'''
					SELECT t1.*
					FROM
						(
							SELECT {0}
							FROM user_log
						) t1
					INNER JOIN
						(
							SELECT DISTINCT userid
							FROM user_sim_log
							WHERE simid in ({1})
						) t2
					ON t1.userid = t2.userid;
					'''.format(cols, simid), dbconnection)

				print("user_log extracted")

			except BaseException as e:
				print('ERROR*** : '+ str(e))



		# 4. Get User Group data
		if extract_user_group:
			try:
				# Get list of columns in table and amend for 'bit' variables
				cols = pd.read_sql_query("SHOW COLUMNS FROM user_group;", dbconnection)
				cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

				dict_data['user_group'] = pd.read_sql_query("SELECT {0} FROM user_group;".format(cols), dbconnection)

				print("user_group extracted")

			except BaseException as e:
				print('ERROR*** : '+ str(e))



		# 5. Get Dialogue Score Log
		if extract_dialogue_score_log:
			try:
				dict_data['dialogue_score_log'] = pd.read_sql_query(
				'''
				SELECT
					t1.*
				FROM
					dialogue_score_log AS t1
				INNER JOIN
					(
						SELECT DISTINCT logid
						FROM user_sim_log
						WHERE simid in ({0})
					) AS t2
				ON t1.logid = t2.logid
				;
				'''.format(simid), dbconnection)

				print("dialogue_score_log extracted")

			except BaseException as e:
				print('ERROR*** : '+ str(e))






		# 6. Extract Quiz Options and Answers if Sim has any Quiz data
		if extract_quiz_data:
			print('Quiz Question Rows: ', dict_data['quiz_question'].shape[0])
			if dict_data['quiz_question'].shape[0] > 0:
				for quiz_tbl in ['quiz_answer','quiz_option']:
					try:
						# Get list of columns in table and amend for 'bit' variables
						cols = pd.read_sql_query("SHOW COLUMNS FROM {0};".format(quiz_tbl), dbconnection)
						cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

						dict_data[quiz_tbl] = pd.read_sql_query('SELECT {0} FROM {1} WHERE questionid IN ({2});'.format(cols, quiz_tbl, dict_data['quiz_question']['questionid'].astype(str).str.cat(sep=', ')), dbconnection)
						print("{} extracted".format(quiz_tbl))

					except BaseException as e:
						print('ERROR*** : '+ str(e))


		# 7. Get Ranking data
		if extract_user_dialogue_rank:
			try:
				# Get list of columns in table and amend for 'bit' variables
				cols = pd.read_sql_query("SHOW COLUMNS FROM user_dialogue_rank;", dbconnection)
				cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

				dict_data['user_dialogue_rank'] = pd.read_sql_query("SELECT {0} FROM user_dialogue_rank;".format(cols, simid), dbconnection)

				print("user_dialogue_rank extracted")

			except BaseException as e:
				print('ERROR*** : '+ str(e))



		# 8. Get Language table
		if extract_language:
			try:
				# Get list of columns in table and amend for 'bit' variables
				cols = pd.read_sql_query("SHOW COLUMNS FROM language;", dbconnection)
				cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

				dict_data['language'] = pd.read_sql_query("SELECT {0} FROM language;".format(cols), dbconnection)

				print("language extracted")

			except BaseException as e:
				print('ERROR*** : '+ str(e))


		# 9. Extract Knowledge Check Options and Answers if Sim has any Knowledge Check data
		if extract_knowledge_check:
			print('Knowledge Question Rows: ', dict_data['knowledge_question'].shape[0])
			if dict_data['knowledge_question'].shape[0] > 0:
				for knowledge_tbl in ['knowledge_option', 'knowledge_answer']:
					try:
						# Get list of columns in table and amend for 'bit' variables
						cols = pd.read_sql_query("SHOW COLUMNS FROM {0};".format(knowledge_tbl), dbconnection)
						cols = ','.join(cols.apply(lambda x: bit_var(x.Type, x.Field), axis=1))

						varname = 'questionid' if knowledge_tbl == 'knowledge_option' else 'optionid'

						dict_data[knowledge_tbl] = pd.read_sql_query('SELECT {0} FROM {1} WHERE {2} IN ({3});'.format(cols, knowledge_tbl, varname, dict_data['knowledge_question'][varname].astype(str).str.cat(sep=', ')), dbconnection)
						print("{} extracted".format(knowledge_tbl))


					except BaseException as e:
						print('ERROR*** : '+ str(e))


		# Close database connection
		dbconnection.close()
		print(server, ': Database connection closed')

		# Close SSH tunnel
		tunnel.close()
		print(server, ': Tunnel closed')

		del dbconnection, tunnel


		return dict_data

# ------------------------------------------------------->
# ----- Function for extracting Sim Data for Report ----->
# ------------------------------------------------------->

# ------------------------------------------------------->
# ----- Function for extracting Sim Data for Report ----->
# ------------------------------------------------------->

def extract_data(
	customer,
	sim_id, # List of Sim IDs
	start_date, # List of Sim Start Dates (or one start date for all Sims)
	end_date, # List of Sim ENd Dates (or one start date for all Sims)
	user_groups=None, # List of character or numeric user groups
	uid_list=None, # Optional list of specific user IDs (uid) to filter the data for.

	learner_engagement=True,
	learner_engagement_over_time=True,
	overall_pass_rates=True,
	skill_pass_rates=False,
	skill_baseline=True,
	skill_improvement=True,
	decision_levels=True,
	time_spent=True,
	practice_mode=True,
	behaviors=True,
	knowledge_check=True,
	survey=True,

	show_hidden_skills=True,
	show_survey_comments=True,
	survey_comment_limit=None, # Integer to limit the number of comments from each free-text question
	survey_topic_analysis=True,

	dict_project=None, # Dictionary linking multiple Sim IDs to prokect(s). This will create data for the "Course Summary" tab of dashboard

	df_demog=None, # Name of dataframe containing demographics. The dataframe must contain "uid" as the learner ID for merging. Demographic analyses are done on all other variables in dataframe
	demog_learners_only=False, # Only get data for learners that exist in bothe the database and the demographics dataframe
	demog_case_sensitive=True, # Should merging on UID be case-sensitive

	merge_simid=None, # A dictionary of Sims that need to be merged together

	dict_manual_levels=None, # A dictionary with manual changes to Sim Levels
	save_df_xml=False, # Save df_xml to dict_df
	learner_engagement_last_7_days= False,
	):
	"""
	Extracts and summarizes data from simulations in standardized formats.

	Args:
		customer (str): The customer identifier.
		sim_id (list): List of simulation IDs.
		start_date (str): List of simulation start dates or a single start date for all simulations.
		end_date (str): List of simulation end dates or a single end date for all simulations.
		user_groups (list, optional): List of character or numeric user groups. Defaults to None.
		uid_list (list, optional): A specific list of user IDs (uid) to pull data for. If provided, this filter takes precedence over the demographics file filter. Defaults to None.
		learner_engagement (bool, optional): Flag to include learner engagement data. Defaults to True.
		learner_engagement_over_time (bool, optional): Flag to include learner engagement over time data. Defaults to True.
		overall_pass_rates (bool, optional): Flag to include overall pass rates data. Defaults to True.
		skill_pass_rates (bool, optional): Flag to include skill pass rates data. Defaults to False.
		skill_baseline (bool, optional): Flag to include skill baseline data. Defaults to True.
		skill_improvement (bool, optional): Flag to include skill improvement data. Defaults to True.
		decision_levels (bool, optional): Flag to include decision levels data. Defaults to True.
		time_spent (bool, optional): Flag to include time spent data. Defaults to True.
		practice_mode (bool, optional): Flag to include practice mode data. Defaults to True.
		behaviors (bool, optional): Flag to include behaviors data. Defaults to True.
		knowledge_check (bool, optional): Flag to include knowledge check data. Defaults to True.
		survey (bool, optional): Flag to include survey data. Defaults to True.
		show_hidden_skills (bool, optional): Flag to include hidden skills in the data. Defaults to True.
		show_survey_comments (bool, optional): Flag to include survey comments in the data. Defaults to True.
		survey_comment_limit (int, optional): Integer to limit the number of comments from each free-text question. Defaults to None.
		survey_topic_analysis (bool, optional): Flag to include survey topic analysis. Defaults to True.
		dict_project (dict, optional): Dictionary linking multiple Sim IDs to project(s). This will create data for the "Course Summary" tab of the dashboard. Defaults to None.
		df_demog (pandas.DataFrame, optional): DataFrame containing demographics. The DataFrame must contain "uid" as the learner ID for merging. Demographic analyses are done on all other variables in the DataFrame. Defaults to None.
		demog_learners_only (bool, optional): Only get data for learners that exist in both the database and the demographics DataFrame. Defaults to False.
		demog_case_sensitive (bool, optional): Should merging on UID be case-sensitive. Defaults to True.
		merge_simid (dict, optional): A dictionary of Sims that need to be merged together. Defaults to None.
		dict_manual_levels (dict, optional): A dictionary with manual changes to Sim Levels. Defaults to None.

	Returns:
		dict: A dictionary containing the extracted and summarized data.
	"""
	# --- Get database properties and credentials --->

	# Get RDS ID and Region of Customer database
	db_rds_endpoint, db_rds_port, db_rds_region = find_rds(customer)
	print('### db_rds_endpoint:', db_rds_endpoint, '### db_rds_port:', db_rds_port)

	db_user = 'etu_data'
	#db_user = 'root'
	db_name = 'etu_sim'

	# Extract the decrypted password
	ssm_client = boto3.client('ssm', region_name=db_rds_region)
	response = ssm_client.get_parameter(
		Name='/appliedscience/mysql-password', # etu_data
		#Name='mysql-root', # root
		WithDecryption=True
	)

	db_password = response['Parameter']['Value']
	ssm_client.close()

	# <--- Get database properties and credentials ---



	# --- Get EC2 ID and Region -->

	ec2_id, ec2_region = find_ec2(customer)
	print('### ec2_id:', ec2_id, '### ec2_region:', ec2_region)

	# <--- Get EC2 ID and Region ---


	# --- Get S3 Bucket properties --->

	s3_bucket_name, s3_region = find_s3(customer)
	print('### s3_bucket_name:', s3_bucket_name, '### s3_region:', s3_region)

	# <--- Get S3 Bucket properties ---

	user_groups_merge = "LEFT" if user_groups == None else "INNER"

	# --- Create SSH Tunnel to client server --->
	try:
		tunnel = sshtunnel(
			ec2_id,
			credentials,
			remote_address=db_rds_endpoint,
			remote_port=db_rds_port,
			local_port=port
		)
		print('SSH Tunnel open')

	except:
		pass


	# --- Establish a connection to the RDS database --->
	try:
		db_connection = pymysql.connect(
			#host=db_rds_endpoint,
			host=tunnel.local_bind_host,
			port=tunnel.local_bind_port,
			user=db_user,
			password=db_password,
			db=db_name
		)

	except:
		pass



	dict_sql = {
		"proj": {},
		"sim": {},
		"srv": {},
		"dmg": {},
	}

	dict_df = {
		"proj": {},
		"sim": {},
		"srv": {},
		"dmg": {},
	}



	# Order of Sims
	def_sim_order = '''CASE'''
	dict_sim_order = {}
	for i, simid in enumerate(sim_id):
		dict_sim_order.update({simid: i})

		def_sim_order+='''
		WHEN simid = {0} THEN {1}
		'''.format(simid, i)


	def_sim_order+='''
	END AS sim_order
	'''


	# --- Define UID filter for SQL queries --->
	cmp_uid = ''
	target_uids = []

	# Prioritize the new uid_list parameter for filtering
	if uid_list is not None and len(uid_list) > 0:
		target_uids = list(pd.Series(uid_list).unique())
	# Fallback to the original demographics file logic
	elif df_demog is not None and demog_learners_only:
		target_uids = list(df_demog['uid'].unique())

	# If there are UIDs to filter by, construct the SQL clause
	if len(target_uids) > 0:
		# Handle potential quotes in UIDs by escaping them
		if demog_case_sensitive:
			formatted_uids = ','.join(['"' + str(uid).replace('"', '""') + '"' for uid in target_uids])
			cmp_uid = f'AND uid IN ({formatted_uids})'
		else:
			formatted_uids = ','.join(['"' + str(uid).lower().replace('"', '""') + '"' for uid in target_uids])
			cmp_uid = f'AND LOWER(uid) IN ({formatted_uids})'



	# Re-define SIMID based on merging Sims together
	list_simid = sim_id.copy()
	if merge_simid is not None:

		def_simid = '''CASE'''
		for key in merge_simid:

			def_simid += '''
			WHEN simid in ({0}) THEN {1}'''.format(','.join([str(x) for x in key]), merge_simid[key])

			for key2 in key:
				if key2 != merge_simid[key]:
					list_simid.remove(key2)

		def_simid += '''
		ELSE simid
		END'''

	else:
		def_simid = 'simid'





	# --- LIST OF SIMS --->

	dict_sql['sim']['sims'] = '''
	SELECT {1} ,simid ,TRIM(`name`) AS simname
	FROM simulation
	WHERE simid IN ({0})
	ORDER BY 1;
	'''.format(
		', '.join([str(x) for x in list_simid]),
		def_sim_order
	)

	dict_df['sim']['sims'] = pd.DataFrame()

	# <--- LIST OF SIMS ---





	# --- LEARNER ENGAGEMENT --->

	if learner_engagement:
		dict_df['sim']['learner_engagement'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))



		dict_sql['sim']['learner_engagement'] = '''
		SELECT simid ,simname
		  ,CAST(total AS UNSIGNED) AS total
		  ,stat_order ,stat
		  ,bar_color
		  ,n
		  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
		FROM
		(
		  SELECT t1.*
			,SUM(CASE WHEN t1.stat_order in (1, 2) AND t2.n IS NOT NULL THEN t2.n ELSE 0 END) OVER (PARTITION BY t1.simid) AS total
			,CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END AS n
		  FROM
		  (
			SELECT *
			FROM
			(
			  SELECT 1 AS stat_order ,"Not Completed" AS stat ,'#d3d2d2' AS bar_color
			  UNION
			  SELECT 2 AS stat_order ,"Completed" AS stat ,'#4285f4' AS bar_color
			  UNION
			  SELECT 3 AS stat_order ,"2 or more" AS stat ,'#2674f2' AS bar_color
			  UNION
			  SELECT 4 AS stat_order ,"3 or more" AS stat ,'#0d5bd9' AS bar_color
			  UNION
			  SELECT 5 AS stat_order ,"4 or more" AS stat ,'#0a47a9' AS bar_color
			) AS t1_1,
			(
				SELECT simid, TRIM(`name`) AS simname
				FROM simulation
				WHERE simid IN ({5})
			) AS t1_2
		  ) AS t1

		  LEFT JOIN
		  (
			WITH
			  stats_tbl AS
			  (
				SELECT *
				FROM
				(
				  SELECT t2_1.simid ,t2_1.userid ,t2_1.start_dt
					,SUM(t2_1.complete) AS n_complete
					,MAX(t2_1.dt) AS dt
				  FROM
					(
					  SELECT {6} AS simid ,userid ,complete
						  ,CASE WHEN complete = 1 THEN `end` ELSE `start` END AS dt
						  ,MIN(DATE(`start`)) OVER (PARTITION BY {6} ,userid) AS start_dt
					  FROM user_sim_log
					  WHERE simid IN ({0}) AND CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}'
					) AS t2_1

				  INNER JOIN
					(
					  SELECT t2_2_1.userid
					  FROM
						(SELECT userid ,groupid FROM user WHERE roleid = 1 {4}) AS t2_2_1
						{7} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_2_2
						ON t2_2_1.groupid = t2_2_2.groupid
					) AS t2_2
				  ON t2_1.userid = t2_2.userid

				  GROUP BY 1, 2, 3
				) AS t2_0
				WHERE start_dt >= "{2}"
			  )

			  SELECT simid ,1 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete = 0 GROUP BY 1, 2
			  UNION ALL
			  SELECT simid ,2 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete >= 1 GROUP BY 1, 2
			  UNION ALL
			  SELECT simid ,3 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete >= 2 GROUP BY 1, 2
			  UNION ALL
			  SELECT simid ,4 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete >= 3 GROUP BY 1, 2
			  UNION ALL
			  SELECT simid ,5 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete >= 4 GROUP BY 1, 2

		  ) AS t2
		  ON t1.simid = t2.simid AND t1.stat_order = t2.stat_order
		) AS t0
		ORDER BY 1, 4;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,
			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- LEARNER ENGAGEMENT ---






	# --- LEARNER ENGAGEMENT OVER TIME --->

	if learner_engagement_over_time:

		dict_df['sim']['learner_engagement_over_time'] = pd.DataFrame()

		period_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1

		time_freq = 'd' if period_days <= 30\
		else 'w' if period_days <= 112\
		else 'm' if period_days <= 730\
		else 'q' if period_days <= 1460\
		else 'y'

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		date_calculation = 'dt + INTERVAL 0 HOUR' if time_freq == 'd'\
		else 'DATE_ADD(dt, INTERVAL -WEEKDAY(dt) DAY)' if time_freq == 'w'\
		else 'DATE(CONCAT(CAST(YEAR(dt) AS CHAR(4)), "-", CAST(MONTH(dt) AS CHAR(4)), "-01"))' if time_freq == 'm'\
		else 'MAKEDATE(YEAR(dt), 1) + INTERVAL (QUARTER(dt)-1) QUARTER' if time_freq == 'q'\
		else 'DATE(CONCAT(CAST(YEAR(dt) AS CHAR(4)), "-01-01"))'

		date_format = 'DATE_FORMAT(dt, "%b %d, %Y")' if time_freq == 'd'\
		else 'DATE_FORMAT(dt, "%b %d, %Y")' if time_freq == 'w'\
		else 'DATE_FORMAT(dt, "%b %Y")' if time_freq == 'm'\
		else 'CONCAT("Q", CAST(QUARTER(dt) AS CHAR(1)), " ", DATE_FORMAT(dt, "%Y"))' if time_freq == 'q'\
		else 'DATE_FORMAT(dt, "%Y")'


		dict_sql['sim']['learner_engagement_over_time'] = '''
		SELECT simid ,simname
		  ,"{6}" AS time_freq
		  ,dt
		  ,{5} AS dt_char
		  ,'#4285f4' AS bar_color
		  ,CAST(total AS UNSIGNED) AS total
		  ,n
		  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
		  ,n_cum
		FROM
		(
		  SELECT t1.*
			,SUM(CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END) OVER (PARTITION BY t1.simid) AS total
			,CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END AS n
			,SUM(CASE WHEN t2.n IS NOT NULL THEN t2.n ELSE 0 END) OVER (PARTITION BY t1.simid ORDER BY t1.dt) AS n_cum
		  FROM
		  (
			SELECT *
			FROM
			(
			  SELECT simid, TRIM(`name`) AS simname FROM simulation WHERE simid IN ({8})
			) AS t1_1,
			(
			  SELECT
				  DISTINCT {4} AS dt
			  FROM
			  (
				  SELECT ADDDATE('1970-01-01',t4.i*10000 + t3.i*1000 + t2.i*100 + t1.i*10 + t0.i) AS dt
				  FROM
				   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t0,
				   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t1,
				   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t2,
				   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t3,
				   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t4
			  ) AS t1_2_0
			  WHERE dt BETWEEN '{2}' AND '{3}'
			) AS t1_2
		  ) AS t1

		  LEFT JOIN
		  (
			WITH
			  stats_tbl AS
			(
			  SELECT t2_1.simid ,t2_1.userid ,t2_1.start_dt
				,MIN(dt) AS dt
			  FROM
				(
				  SELECT {9} AS simid ,userid ,complete ,DATE(`end`) AS dt
					,MIN(DATE(`start`)) OVER (PARTITION BY {9} ,userid) AS start_dt
				  FROM user_sim_log
				  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
				) AS t2_1

			  INNER JOIN
				(
				  SELECT t2_3_1.userid
				  FROM
					(SELECT userid ,groupid FROM user where roleid = 1 {7}) AS t2_3_1
					{10} JOIN
					(SELECT groupid FROM user_group {1}) AS t2_3_2
					ON t2_3_1.groupid = t2_3_2.groupid
				) AS t2_3
			  ON t2_1.userid = t2_3.userid

			  GROUP BY 1, 2, 3
			)

			SELECT simid
			  ,{4} AS dt
			  ,COUNT(*) AS `n`
			FROM stats_tbl
			WHERE start_dt >= "{2}"
			GROUP BY 1, 2
		  ) AS t2

		  ON t1.simid = t2.simid AND t1.dt = t2.dt
		) AS t0
		ORDER BY 4, 1;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			date_calculation,
			date_format,
			time_freq,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- LEARNER ENGAGEMENT OVER TIME ---






	# --- OVERALL PASS RATES --->

	if overall_pass_rates:

		dict_df['sim']['overall_pass_rates'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		dict_sql['sim']['overall_pass_rates'] = '''
		SELECT simid ,simname ,n_skills
		  ,CAST(total AS UNSIGNED) AS total
		  ,stat_order ,stat
		  ,bar_color
		  ,n
		  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
		FROM
		(
		  SELECT t1.*
			,SUM(CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END) OVER (PARTITION BY t1.simid) AS total
			,CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END AS n
		  FROM
		  (
			SELECT *
			FROM
			(
			  SELECT 1 AS stat_order ,"1" AS stat ,'#339933' AS bar_color
			  UNION
			  SELECT 2 AS stat_order ,"2" AS stat ,'#53c653' AS bar_color
			  UNION
			  SELECT 3 AS stat_order ,"3" AS stat ,'#8cd98c' AS bar_color
			  UNION
			  SELECT 4 AS stat_order ,"4+" AS stat ,'#c6ecc6' AS bar_color
			  UNION
			  SELECT 5 AS stat_order ,"Completed, not yet Passed" AS stat ,'#e32726' AS bar_color
			) AS t1_1,
			(
				SELECT t1_2_1.* ,CASE WHEN t1_2_2.n_skills IS NOT NULL THEN t1_2_2.n_skills ELSE 0 END AS n_skills
				FROM
				(
					SELECT simid, TRIM(`name`) AS simname FROM simulation WHERE simid IN ({5})
				) AS t1_2_1

				LEFT JOIN
				(
				  SELECT simid ,SUM(CASE WHEN bench > 0 THEN 1 ELSE 0 END) AS n_skills
				  FROM score
				  WHERE simid IN ({5})
				  GROUP BY 1
				) AS t1_2_2
				ON t1_2_1.simid = t1_2_2.simid
			) AS t1_2
		  ) AS t1

		  LEFT JOIN
		  (
			WITH
			  stats_tbl AS
			(
			  SELECT *
				,CASE
				  WHEN max_user_complete = 1 AND max_user_pass = 0 AND `end` = min_user_end THEN min_user_end
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND pass = 1 AND min_pass_attempt = 4 AND `end` = min_pass_end THEN `end`
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND pass = 1 AND min_pass_attempt = 3 AND attempt = 3 THEN `end`
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND pass = 1 AND min_pass_attempt = 2 AND attempt = 2 THEN `end`
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND pass = 1 AND min_pass_attempt = 1 AND attempt = 1 THEN `end`
				END AS dt
				,CASE
				  WHEN max_user_complete = 1 AND max_user_pass = 0 AND `end` = min_user_end THEN 5
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND `pass` = 1 AND min_pass_attempt = 4 AND `end` = min_pass_end THEN 4
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND `pass` = 1 AND min_pass_attempt = 3 AND attempt = 3 THEN 3
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND `pass` = 1 AND min_pass_attempt = 2 AND attempt = 2 THEN 2
				  WHEN max_user_complete = 1 AND max_user_pass = 1 AND `pass` = 1 AND min_pass_attempt = 1 AND attempt = 1 THEN 1
				END AS stat_order
			  FROM
			  (
				SELECT *
				  ,MIN(`end`) OVER (PARTITION BY simid ,userid) AS min_user_end
				  ,MAX(complete) OVER (PARTITION BY simid ,userid) AS max_user_complete
				  ,MAX(`pass`) OVER (PARTITION BY simid ,userid) AS max_user_pass

				  ,MIN(`end`) OVER (PARTITION BY simid ,userid ,`pass`) AS min_pass_end
				  ,MIN(CASE WHEN attempt >= 4 THEN 4 ELSE attempt END) OVER (PARTITION BY simid ,userid ,`pass`) AS min_pass_attempt

				FROM
				(
				  SELECT t2_1.simid ,t2_3.n_skills ,t2_1.userid ,t2_1.start_dt ,t2_1.`pass` ,t2_1.`start` ,t2_1.`end` ,t2_1.complete
				  ,ROW_NUMBER() OVER (PARTITION BY t2_1.simid ,t2_1.userid ORDER BY t2_1.`start`) AS attempt

				  FROM
					(
					  SELECT {6} AS simid ,userid ,complete ,`start` ,`end` ,`pass`
						,MIN(DATE(`start`)) OVER (PARTITION BY {6} ,userid) AS start_dt
					  FROM user_sim_log
					  WHERE simid IN ({0}) AND CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}'
					) AS t2_1

				  INNER JOIN
					(
					  SELECT t2_2_1.userid
					  FROM
						(SELECT userid ,groupid FROM user WHERE roleid = 1 {4}) AS t2_2_1
						{7} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_2_2
						ON t2_2_1.groupid = t2_2_2.groupid
					) AS t2_2
				  ON t2_1.userid = t2_2.userid

				  LEFT JOIN
				  (
					SELECT simid ,SUM(CASE WHEN bench > 0 THEN 1 ELSE 0 END) AS n_skills
					FROM score
					WHERE simid IN ({0})
					GROUP BY 1
				  ) AS t2_3
				  ON t2_1.simid = t2_3.simid
				) AS t2_0_1
			  ) AS t2_0
			)


			SELECT simid ,stat_order ,COUNT(*) AS n
			FROM stats_tbl
			WHERE start_dt >= "{2}"
			GROUP BY 1, 2
		  ) AS t2

		  ON t1.simid = t2.simid AND t1.stat_order = t2.stat_order
		) AS t0
		WHERE stat_order <= 4
		ORDER BY 2, 6;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- OVERALL PASS RATES ---




	# --- SKILL PASS RATES --->

	if skill_pass_rates:

		dict_df['sim']['skill_pass_rates'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		dict_sql['sim']['skill_pass_rates'] = '''
		SELECT simid ,simname ,n_skills
		  ,orderid ,skillname
		  ,CAST(total AS UNSIGNED) AS total
		  ,stat_order ,stat ,stat_suffix
		  ,bar_color
		  ,n
		  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
		  ,SUM(CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END) OVER (PARTITION BY simid ,orderid) AS total_pct
		  ,CONCAT(simname, " (", FORMAT(total, 0), " learners)") AS simname_total
		FROM
		(
		  SELECT t1.*
			-- ,MAX(CASE WHEN t2.complete_any_sim IS NOT NULL THEN t2.complete_any_sim ELSE 0 END) OVER () AS complete_any_sim
			,SUM(CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END) OVER (PARTITION BY t1.simid ,t1.orderid) AS total
			,CASE WHEN t2.n IS NOT NULL THEN t2.n ELSE 0 END AS n
		  FROM
		  (
			SELECT *
			FROM
			(
			  SELECT 1 AS stat_order ,"1" AS stat ,"attempt" AS stat_suffix ,'#339933' AS bar_color
			  UNION
			  SELECT 2 AS stat_order ,"2" AS stat ,"attempts" AS stat_suffix ,'#53c653' AS bar_color
			  UNION
			  SELECT 3 AS stat_order ,"3" AS stat ,"attempts" AS stat_suffix ,'#8cd98c' AS bar_color
			  UNION
			  SELECT 4 AS stat_order ,"4+" AS stat ,"attempts" AS stat_suffix ,'#c6ecc6' AS bar_color
			  UNION
			  SELECT 5 AS stat_order ,"Completed, not yet Passed" AS stat ,"" AS stat_suffix ,'#e32726' AS bar_color
			) AS t1_1,
			(
				SELECT t1_2_1.*
					,CASE WHEN t1_2_2.n_skills IS NOT NULL THEN t1_2_2.n_skills ELSE 0 END AS n_skills
					,t1_2_3.orderid ,t1_2_3.skillname
				FROM
				(
					SELECT simid, TRIM(`name`) AS simname
					FROM simulation
					WHERE simid IN ({5})
				) AS t1_2_1

				LEFT JOIN
				(
				  SELECT simid ,SUM(CASE WHEN bench > 0 THEN 1 ELSE 0 END) AS n_skills
				  FROM score
				  WHERE simid IN ({5})
				  GROUP BY 1
				) AS t1_2_2
				ON t1_2_1.simid = t1_2_2.simid

				LEFT JOIN
				(
				  SELECT simid ,orderid ,REPLACE(TRIM(`label`), '\u200b', '') AS skillname
				  FROM score
				  WHERE simid IN ({5}) AND bench > 0
				) AS t1_2_3
				ON t1_2_1.simid = t1_2_3.simid
			) AS t1_2
		  ) AS t1

		  LEFT JOIN
		  (
			WITH
			  stats_tbl AS
			(
			  SELECT *
				,CASE
				  WHEN max_user_complete = 1 AND max_user_score_pass = 0 AND `end` = min_user_end THEN min_user_end
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND pass = 1 AND min_pass_score_attempt = 4 AND `end` = min_pass_end THEN `end`
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND pass = 1 AND min_pass_score_attempt = 3 AND attempt = 3 THEN `end`
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND pass = 1 AND min_pass_score_attempt = 2 AND attempt = 2 THEN `end`
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND pass = 1 AND min_pass_score_attempt = 1 AND attempt = 1 THEN `end`
				END AS dt
				,CASE
				  WHEN max_user_complete = 1 AND max_user_score_pass = 0 AND `end` = min_user_end THEN 5
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND `pass` = 1 AND min_pass_score_attempt = 4 AND `end` = min_pass_end THEN 4
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND `pass` = 1 AND min_pass_score_attempt = 3 AND attempt = 3 THEN 3
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND `pass` = 1 AND min_pass_score_attempt = 2 AND attempt = 2 THEN 2
				  WHEN max_user_complete = 1 AND max_user_score_pass = 1 AND `pass` = 1 AND min_pass_score_attempt = 1 AND attempt = 1 THEN 1
				END AS stat_order
			  FROM
			  (
				SELECT *
				  ,MIN(`end`) OVER (PARTITION BY simid ,userid) AS min_user_end
				  ,MAX(complete) OVER (PARTITION BY simid ,userid) AS max_user_complete
				  ,MAX(`pass`) OVER (PARTITION BY simid ,orderid ,userid) AS max_user_score_pass

				  ,MIN(`end`) OVER (PARTITION BY simid ,orderid ,userid ,`pass`) AS min_pass_end
				  ,MIN(CASE WHEN attempt >= 4 THEN 4 ELSE attempt END) OVER (PARTITION BY simid ,orderid ,userid ,`pass`) AS min_pass_score_attempt

				FROM
				(
					SELECT t2_1.simid ,t2_3.n_skills ,t2_1.userid ,t2_1.start_dt ,t2_1.`start` ,t2_1.`end` ,t2_1.complete ,t2_1.attempt
						,t2_4.orderid ,t2_4.skillname ,t2_4.`pass`
					FROM
					(
					  SELECT *
						  ,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY `start`) AS attempt
					  FROM
					  (
						  SELECT {6} AS simid ,userid ,logid ,complete ,`start` ,`end`
							  ,MIN(DATE(`start`)) OVER (PARTITION BY {6} ,userid) AS start_dt
						  FROM user_sim_log
						  WHERE simid IN ({0}) AND CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}'
					  ) AS t2_1_0
					) AS t2_1

					INNER JOIN
					(
						SELECT t2_2_1.userid
						FROM
						(SELECT userid ,groupid FROM user WHERE roleid = 1 {4}) AS t2_2_1
						{7} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_2_2
						ON t2_2_1.groupid = t2_2_2.groupid
					) AS t2_2
					ON t2_1.userid = t2_2.userid

					LEFT JOIN
					(
						SELECT simid ,SUM(CASE WHEN bench > 0 THEN 1 ELSE 0 END) AS n_skills
						FROM score
						WHERE simid IN ({0})
						GROUP BY 1
					) AS t2_3
					ON t2_1.simid = t2_3.simid

					LEFT JOIN
					(
						SELECT t2_4_1.simid ,t2_4_1.userid ,t2_4_1.logid
							,t2_4_2.orderid ,REPLACE(TRIM(t2_4_2.`label`), '\u200b', '') AS skillname
							,CASE WHEN t2_4_1.value >= t2_4_2.bench THEN 1 ELSE 0 END AS `pass`
						FROM
						(SELECT * FROM sim_score_log WHERE simid IN ({0})) AS t2_4_1
						INNER JOIN
						(SELECT * FROM score WHERE simid IN ({0}) AND bench > 0) AS t2_4_2
						ON t2_4_1.simid = t2_4_2.simid AND t2_4_1.scoreid = t2_4_2.scoreid
					) AS t2_4
					ON t2_1.simid = t2_4.simid AND t2_1.userid = t2_4.userid AND t2_1.logid = t2_4.logid

				) AS t2_0_1
			  ) AS t2_0
			)


			SELECT simid ,orderid ,skillname ,stat_order ,COUNT(*) AS n
			FROM stats_tbl
			WHERE start_dt >= "{2}"
			GROUP BY 1, 2, 3, 4
		  ) AS t2

		  ON t1.simid = t2.simid AND t1.orderid = t2.orderid AND t1.stat_order = t2.stat_order
		) AS t0
		WHERE stat_order <= 4
		ORDER BY 1, 4, 7;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- SKILL PASS RATES ---





	# --- SKILL SCORES - BASELINE --->

	if skill_baseline:

		dict_df['sim']['skill_baseline'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))
		cmp_show_hidden_skills = "" if show_hidden_skills else 'WHERE hidden = 0'

		dict_sql['sim']['skill_baseline'] = '''
		SELECT t1.simid ,t1.simname ,t1.orderid ,t1.skillname
			,CASE WHEN t1.bench > 0 THEN t1.bench END AS bench
			,t1.hidden
			,CASE WHEN t2.n IS NULL THEN CAST(0 AS UNSIGNED) ELSE CAST(t2.n AS UNSIGNED) END AS n
			,CASE WHEN t2.avg_skillscore IS NULL THEN 0 ELSE t2.avg_skillscore END AS avg_skillscore
			,"First Attempt" AS attempt
			,"#9fdf9f" AS bar_color
		FROM
		(
			SELECT t1_1.* ,t1_2.orderid ,t1_2.skillname ,t1_2.bench ,t1_2.hidden
			FROM
			(
				SELECT simid, TRIM(`name`) AS simname
				FROM simulation
				WHERE simid IN ({6})
			) AS t1_1

			INNER JOIN
			(
				SELECT simid ,orderid ,REPLACE(TRIM(`label`), '\u200b', '') AS skillname ,bench ,hidden
				FROM score
				{4}
			) AS t1_2
			ON t1_1.simid = t1_2.simid
		) AS t1

		LEFT JOIN
		(
			WITH
			  stats_tbl AS
			  (
				SELECT t2_1.simid ,t2_1.userid ,t2_3.scoreid ,t2_4.orderid ,t2_3.value
				FROM
				(
					SELECT *
					FROM
					(
						SELECT *
							,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
							,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS attempt
						FROM
						(
							SELECT DISTINCT {7} AS simid ,userid ,logid ,`start` ,`end` AS dt
							FROM user_sim_log
							WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
						) AS t2_1_1
					) AS t2_1_2
					WHERE attempt = 1 AND start_dt >= "{2}"
				) AS t2_1

				INNER JOIN
				(
					SELECT t2_3_1.userid
					FROM
					(SELECT userid ,groupid FROM user where roleid = 1 {5}) AS t2_3_1
					{8} JOIN
					(SELECT groupid FROM user_group {1}) AS t2_3_2
					ON t2_3_1.groupid = t2_3_2.groupid
				) AS t2_2
				ON t2_1.userid = t2_2.userid

				LEFT JOIN
				(
					SELECT {7} AS simid ,userid ,logid ,scoreid ,value
					FROM sim_score_log
				) AS t2_3
				ON t2_1.simid = t2_3.simid AND t2_1.userid = t2_3.userid AND t2_1.logid = t2_3.logid

				LEFT JOIN
				(
					SELECT {7} AS simid ,scoreid ,orderid
					FROM score
				) AS t2_4
				ON t2_3.simid = t2_4.simid AND t2_3.scoreid = t2_4.scoreid
			  )

			  SELECT t2_0_1.simid ,t2_0_1.n ,t2_0_2.orderid ,t2_0_2.avg_skillscore
			  FROM
			  (SELECT simid, COUNT(DISTINCT userid) AS n FROM stats_tbl GROUP BY 1) AS t2_0_1
			  LEFT JOIN
			  (SELECT simid, orderid, AVG(value) AS avg_skillscore FROM stats_tbl GROUP BY 1, 2) AS t2_0_2
			  ON t2_0_1.simid = t2_0_2.simid
		) AS t2
		ON t1.simid = t2.simid AND t1.orderid = t2.orderid
		ORDER BY 1, 3;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_show_hidden_skills,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- SKILL SCORES - BASELINE ---





	# --- SKILL SCORES - IMPROVEMENT --->

	if skill_improvement:

		dict_df['sim']['skill_improvement'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))
		cmp_show_hidden_skills = "" if show_hidden_skills else 'WHERE hidden = 0'

		dict_sql['sim']['skill_improvement'] = '''
		SELECT t1.simid ,t1.simname ,t1.orderid ,t1.skillname
			,CASE WHEN t1.bench > 0 THEN t1.bench END AS bench
			,t1.hidden
			-- ,CASE WHEN t2.n IS NULL THEN CONCAT(t1.attempt, "<br>(", FORMAT(0, 0), " Learners)") ELSE CONCAT(t1.attempt, "<br>(", FORMAT(t2.n, 0), " Learners)") END AS attempt
			,t1.attempt
			,t1.bar_color
			,CASE WHEN t2.n IS NULL THEN CAST(0 AS UNSIGNED) ELSE CAST(t2.n AS UNSIGNED) END AS n
			,CASE WHEN t2.avg_skillscore IS NULL THEN 0 ELSE t2.avg_skillscore END AS avg_skillscore
			,t2.avg_chg_skillscore
		FROM
		(
			SELECT *
			FROM
			(
				SELECT t1_1_1.* ,t1_1_2.orderid ,t1_1_2.skillname ,t1_1_2.bench ,t1_1_2.hidden
				FROM
				(
					SELECT simid, TRIM(`name`) AS simname
					FROM simulation
					WHERE simid IN ({6})
				) AS t1_1_1

				INNER JOIN
				(
					SELECT simid, orderid ,REPLACE(TRIM(`label`), '\u200b', '') AS skillname ,bench ,hidden
					FROM score
					{4}
				) AS t1_1_2
				ON t1_1_1.simid = t1_1_2.simid
			) AS t1_1,
			(
				SELECT "First Attempt" AS attempt ,"#9fdf9f" AS bar_color
				UNION
				SELECT "Last Attempt" AS attempt ,'#339933' AS bar_color
			) AS t1_2
		) AS t1

		LEFT JOIN
		(
			WITH
			  stats_tbl AS
			  (
				SELECT t2_1.simid ,t2_1.userid ,t2_1.attempt ,t2_3.scoreid ,t2_4.orderid
					,t2_3.skillscore
					,LAG(t2_3.skillscore) OVER (PARTITION BY t2_1.simid ,t2_1.userid ,t2_3.scoreid ORDER BY t2_1.attempt) AS lag_skillscore
				FROM
				(
					SELECT simid ,userid ,logid
						,CASE
							WHEN attempt = 1 THEN "First Attempt"
							WHEN last_attempt = 1 THEN "Last Attempt"
						END AS attempt
					FROM
					(
						SELECT *
							,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
							,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS attempt
							,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt DESC) AS last_attempt
							,SUM(complete) OVER (PARTITION BY simid ,userid) AS n_attempts
						FROM
						(
							SELECT DISTINCT {7} AS simid ,userid ,logid ,`start` ,`end` AS dt ,complete
							FROM user_sim_log
							WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
						) AS t2_1_1
					) AS t2_1_2
					WHERE start_dt >= "{2}" AND n_attempts > 1 AND (attempt = 1 OR last_attempt = 1)
				) AS t2_1

				INNER JOIN
				(
					SELECT t2_3_1.userid
					FROM
					(SELECT userid ,groupid FROM user where roleid = 1 {5}) AS t2_3_1
					{8} JOIN
					(SELECT groupid FROM user_group {1}) AS t2_3_2
					ON t2_3_1.groupid = t2_3_2.groupid
				) AS t2_2
				ON t2_1.userid = t2_2.userid

				LEFT JOIN
				(
					SELECT {7} AS simid ,userid ,logid ,scoreid ,value AS skillscore
					FROM sim_score_log
				) AS t2_3
				ON t2_1.simid = t2_3.simid AND t2_1.userid = t2_3.userid AND t2_1.logid = t2_3.logid

				LEFT JOIN
				(
					SELECT {7} AS simid ,scoreid ,orderid
					FROM score
				) AS t2_4
				ON t2_3.simid = t2_4.simid AND t2_3.scoreid = t2_4.scoreid
			  )

			  SELECT t2_0_1.simid ,t2_0_1.attempt ,t2_0_2.orderid ,t2_0_1.n ,t2_0_2.avg_skillscore ,t2_0_2.avg_chg_skillscore
			  FROM
			  (SELECT simid ,attempt, COUNT(DISTINCT userid) AS n FROM stats_tbl GROUP BY 1, 2) AS t2_0_1
			  LEFT JOIN
			  (SELECT simid ,attempt ,orderid ,AVG(skillscore) AS avg_skillscore ,AVG(skillscore-lag_skillscore) AS avg_chg_skillscore FROM stats_tbl GROUP BY 1, 2, 3) AS t2_0_2
			  ON t2_0_1.simid = t2_0_2.simid AND t2_0_1.attempt = t2_0_2.attempt

		) AS t2
		ON t1.simid = t2.simid AND t1.orderid = t2.orderid AND t1.attempt = t2.attempt
		ORDER BY 1, 3, 7;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_show_hidden_skills,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge
		)

	# <--- SKILL SCORES - IMPROVEMENT ---





	# --- Get XML files for Decision Levels and Behaviors/Consequences --->

	if decision_levels or behaviors:

		# Get XML file locations
		df_xml_files = pd.read_sql_query(
			'SELECT simid, TRIM(`name`) AS simname, fileUrl FROM simulation WHERE simid IN ({0});'.format(', '.join([str(x) for x in sim_id])),
			db_connection
		)
	
		# Get XML file locations
		list_xml = []
		for i, row in df_xml_files.iterrows():

			# --- Copy the XML file from EC2 Instance to S3 Bucket --->

			ec2_xml_source_file = '/usr/local/etu_sims/' + row['fileUrl']
			s3_xml_destination_file = 'appsciences/xml/' + '/'.join(row['fileUrl'].split('/')[1:])

			# Connect to S3
			s3 = boto3.client('s3', region_name=s3_region)

			# Open SSM connection
			ssm_client = boto3.client('ssm', region_name=ec2_region)

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

			this_xml_as_df = xml_to_df(xml_content, split_score=True)
		
			if isinstance(this_xml_as_df, pd.DataFrame):
				list_xml.append(
					this_xml_as_df\
					.assign(
						relationid = lambda x: x.apply(lambda y: str(y['startingpoint']) + '-' + str(y['id']), axis=1),
						relationtype = lambda x: x['qtype'].apply(lambda y: 1 if y == 'critical' else 2 if y == 'suboptimal' else 3 if y == 'optimal' else 4),
						decisiontype = lambda x: x['qtype'].apply(lambda y: y.capitalize() if pd.notnull(y) else None),
						simid = row['simid']
					)
				)
		
			# Delete XML file from S3 Bucket
			session = boto3.Session(region_name=s3_region)
			s3_session = session.resource('s3')

			s3_session.Object(
				s3_bucket_name,
				'appsciences/xml/' + '/'.join(row['fileUrl'].split('/')[1:])
			).delete()
			print(row['fileUrl'] + " copied and deleted from S3 Bucket successfully.")
			
		df_xml = pd.concat(list_xml, ignore_index=True)
		if save_df_xml:
			dict_df['sim']['df_xml'] = df_xml


		# --- Extract decision level data for Behaviors/Consequences --->
		if behaviors:
			cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

			df_sql_decision_level = pd.read_sql_query(
				'''
				SELECT t2_1.simid ,t2_2.simname ,t2_1.userid ,t2_1.logid ,t2_1.attempt ,t2_4.relationid ,t2_4.relationtype AS relationtype ,t2_4.`end`
					,CASE
						WHEN t2_4.relationtype = 1 THEN "Critical"
						WHEN t2_4.relationtype = 2 THEN "Suboptimal"
						WHEN t2_4.relationtype = 3 THEN "Optimal"
					END AS decisiontype
					,CASE
						WHEN t2_4.relationtype = 1 THEN 3
						WHEN t2_4.relationtype = 2 THEN 2
						WHEN t2_4.relationtype = 3 THEN 1
					END AS decision_ord
				FROM
				(
					SELECT simid ,userid ,logid
						,CASE
							WHEN attempt = 1 THEN "First Attempt"
							WHEN last_attempt = 1 THEN "Last Attempt"
						END AS attempt
					FROM
					(
						SELECT *
							,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
							,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS attempt
							,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt DESC) AS last_attempt
							,SUM(complete) OVER (PARTITION BY simid ,userid) AS n_attempts
						FROM
						(
							SELECT DISTINCT {5} AS simid ,userid ,logid ,`start` ,`end` AS dt ,complete
							FROM user_sim_log
							WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
						) AS t2_1_1
					) AS t2_1_2
					WHERE start_dt >= "{2}" AND (attempt = 1 OR (attempt != 1 AND last_attempt = 1))
				) AS t2_1

				INNER JOIN
				(
					SELECT simid, TRIM(`name`) AS simname
					FROM simulation
					WHERE simid IN ({0})
				) AS t2_2
				ON t2_1.simid = t2_2.simid

				INNER JOIN
				(
					SELECT t2_3_1.userid
					FROM
					(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t2_3_1
					{6} JOIN
					(SELECT groupid FROM user_group {1}) AS t2_3_2
					ON t2_3_1.groupid = t2_3_2.groupid
				) AS t2_3
				ON t2_1.userid = t2_3.userid

				LEFT JOIN
				(
					SELECT {5} AS simid ,userid ,logid ,relationid ,relationType ,`end`
					FROM user_dialogue_log
					WHERE simid IN ({0}) AND relationType <= 3 AND relationid IS NOT NULL AND LOCATE("None", relationid) = 0
				) AS t2_4
				ON t2_1.simid = t2_4.simid AND t2_1.userid = t2_4.userid AND t2_1.logid = t2_4.logid;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					cmp_user_groups,
					start_date,
					end_date,
					cmp_uid,
					def_simid,
					user_groups_merge,
				),

				db_connection
			)\
			.query('relationid.notnull()', engine='python')\
			.query('not relationid.str.contains("None")', engine='python')

			print('Decision level data extracted for Behaviors and Consequences')


	# --- DECISION LEVELS --->

	if decision_levels:

		# --- Calculate Decision Levels --->
		list_sim_levels = []
		for idx, row in df_xml.filter(['simid']).drop_duplicates().iterrows():

			sim = row['simid']

			df_this_sim_levels = sim_levels(
				df_xml\
				.query('simid == @sim and not relationid.str.contains("None")', engine='python')\
				.filter(['relationid', 'relationtype', 'performancebranch'])\
				.drop_duplicates()
			)\
			.assign(
				simid = row['simid'],
				#simname = row['simname']
			)

			if df_this_sim_levels.shape[0] > 0:
				df_this_sim_levels = df_this_sim_levels\
				.query('decision_level.str.contains(",")', engine='python')


			if isinstance(df_this_sim_levels, pd.DataFrame) and df_this_sim_levels.shape[0] > 0:

				# --- Get Sections --->
				df_this_sim_levels = df_this_sim_levels\
				.merge(
					df_xml\
					.assign(
						dialogueid = lambda x: x['startingpoint'].apply(lambda y: int(y) if pd.notnull(y) else None),
						sectionid = lambda x: x.groupby(['simid', 'sectionid', 'section'])['y'].transform('min')
					)\
					.filter(['simid', 'dialogueid', 'sectionid', 'section'])\
					.drop_duplicates(),

					how='left',
					on=['simid', 'dialogueid']
				)\
				.sort_values(['simid', 'decision_level_num', 'decision_level', 'dialogueid', 'sectionid'])\
				.groupby(['simid', 'decision_level_num', 'decision_level', 'dialogueid'])\
				.first()\
				.reset_index()\
				.sort_values(['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'dialogueid'])


				# Get unique Decision Level Number (based on sort order)
				df_this_sim_levels = df_this_sim_levels\
				.drop(columns=['decision_level_num'])\
				.merge(
					df_this_sim_levels\
					.filter(['simid', 'sectionid', 'section', 'decision_level'])\
					.drop_duplicates()\
					.assign(
					  decision_level_num = lambda x: x.groupby(['simid'])['decision_level'].cumcount()+1
					),

					how='left',
					on=['simid', 'sectionid', 'section', 'decision_level']
				)


				# --- Get Scenario to decision --->
				df_this_sim_levels = df_this_sim_levels\
				.merge(
					df_xml\
					.assign(
						dialogueid = lambda x: x['relationid'].apply(lambda y: int(y.split('-')[1]) if pd.notnull(y) else None),
						decision_type = lambda x: x['qtype'].apply(lambda y: 1 if y == 'optimal' else 2 if y == 'suboptimal' else 3 if y == 'critical' else 4)
					)\
					.filter(['simid', 'dialogueid', 'result', 'decision_type'])\
					.drop_duplicates()\
					.rename(columns={'result':'scenario'})\
					.merge(
						df_this_sim_levels\
						.filter(['simid', 'dialogueid', 'decision_level_num', 'decision_level']),

						how='inner',
						on=['simid', 'dialogueid']
					)\
					.sort_values(['simid', 'decision_level_num', 'decision_level', 'decision_type', 'dialogueid'])\
					.groupby(['simid', 'decision_level_num', 'decision_level'])\
					.first()\
					.reset_index()\
					.filter(['simid', 'decision_level_num', 'decision_level', 'scenario'])\
					.drop_duplicates(),

					how='left',
					on=['simid', 'decision_level_num', 'decision_level']
				)\
				.assign(
				  scenario = lambda x: x.apply(lambda y: 'Decision Level #' + str(int(y['decision_level_num'])) if pd.isnull(y['scenario']) else y['scenario'], axis=1)
				)


				# --- Add white space to "scenarios" that are used on multiple Decision Levels (this helps with the JS graphs) --->
				df_this_sim_levels = df_this_sim_levels\
				.drop(columns=['scenario'])\
				.merge(
					df_this_sim_levels\
					.filter(['simid', 'scenario', 'decision_level_num', 'decision_level'])\
					.drop_duplicates()\
					.assign(
						scenario_dec_num = lambda x: x.groupby(['simid', 'scenario'])['decision_level'].cumcount(),
						scenario = lambda x: x.apply(lambda y: y['scenario'] + ' '*int(y['scenario_dec_num']) if pd.notnull(y['scenario_dec_num']) else y['scenario'], axis=1)
					)\
					.drop(columns=['scenario_dec_num']),

					how='left',
					on=['simid', 'decision_level_num', 'decision_level']
				)

				list_sim_levels.append(df_this_sim_levels)



		df_sim_levels = pd.concat(list_sim_levels, ignore_index=True)



		df_sim_model_levels = df_sim_levels\
		.merge(
			df_xml\
			.query('relationid.notnull() and not relationid.str.contains("None")', engine='python')\
			.filter(['simid', 'relationid', 'decisiontype', 'choice', 'feedback', 'coaching'])\
			.drop_duplicates()\
			.assign(
				dialogueid = lambda x: x['relationid'].apply(lambda y: int(y.split('-')[0]))
			),
			how='left',
			on=['simid', 'dialogueid']
		)

		df_sim_model_levels = df_sim_model_levels\
		.merge(
			df_sim_model_levels
			.filter(['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decisiontype', 'choice'])\
			.drop_duplicates()\
			.assign(
				choice_num = lambda x: x.groupby(['simid', 'sectionid', 'decision_level', 'decisiontype'])['choice'].cumcount()+1
			),

			how='left',
			on=['simid', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decisiontype', 'choice']
		)

		#if df_this_sim_levels.shape[0] > 0:
		#    df_sim_levels = df_sim_levels\
		#    .query('decision_level.str.contains(",") and performancebranch != 1', engine='python')

		del list_sim_levels



		# --- Manually change Sim Levels, if needed --->
		if dict_manual_levels is not None:

			for key_manual, val_manual in dict_manual_levels.items():
				list_simid_manual = list(key_manual) if isinstance(key_manual, tuple) else [key_manual]

				for simid_manual in list_simid_manual:
					for key_level, val_level in val_manual.items():
						df_sim_levels = df_sim_levels\
						.assign(
							decision_level = lambda x: x.apply(lambda y: val_level if y['simid'] == simid_manual and y['decision_level'] in key_level else y['decision_level'], axis=1)
						)

						df_sim_model_levels = df_sim_model_levels\
						.assign(
							decision_level = lambda x: x.apply(lambda y: val_level if y['simid'] == simid_manual and y['decision_level'] in key_level else y['decision_level'], axis=1)
						)



		print('Decision levels calculated')

		# <--- Calculate Decision Levels ---





		# --- Summarize Data --->

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))
		cmp_show_hidden_skills = "" if show_hidden_skills else 'WHERE hidden = 0'


		# Define Sim Level in SQL
		decision_level = df_sim_model_levels\
		.filter(['simid', 'decision_level_num', 'relationid'])\
		.drop_duplicates()

		def_decision_level = '''CASE'''

		for sim in decision_level['simid'].unique():
			for dec_level in decision_level.query('simid == @sim')['decision_level_num'].unique():
				def_decision_level += '''
				WHEN simid = {0} AND relationid IN ({1}) THEN {2}
				'''.format(
					str(sim),
					",".join(['"' + str(x) + '"' for x in decision_level.query('simid == @sim and decision_level_num == @dec_level')['relationid']]),
					dec_level
				)

		def_decision_level += '''
		END AS decision_level_num
		'''


		# Define choice in SQL
		if df_sim_model_levels['choice_num'].max() > 1:
			print('MULTIPLE CHOICES!')

			choice = df_sim_model_levels\
			.filter(['simid', 'choice_num', 'relationid'])\
			.drop_duplicates()

			def_choice = '''CASE'''

			for sim in choice['simid'].unique():
				for id in choice.query('simid == @sim')['choice_num'].unique():

					if id > 1:
						def_choice += '''
						WHEN simid = {0} AND relationid IN ({1}) THEN {2}
						'''.format(
							str(sim),
							",".join(['"' + str(x) + '"' for x in choice.query('simid == @sim and choice_num == @id')['relationid']]),
							str(id)
						)

			def_choice += '''
			ELSE 1
			END AS choice_num
			'''

		else:
			def_choice = '''
			1 AS choice_num
			'''



		df_sql = pd.read_sql_query(
			'''
			WITH stats_tbl AS
			(
				SELECT t2_1.simid ,t2_2.simname ,t2_1.attempt ,t2_4.decision_level_num ,t2_4.decision_ord ,t2_4.decisiontype ,t2_4.choice_num ,t2_1.userid
					,ROW_NUMBER() OVER (PARTITION BY t2_1.simid ,t2_1.attempt ,t2_4.decision_level_num ,t2_1.userid ORDER BY t2_4.`end` DESC) AS dec_num
				FROM
				(
				  SELECT *
					  ,CASE
						  WHEN first_attempt = 1 THEN "First Attempt"
						  WHEN last_attempt = 1 THEN "Last Attempt"
					  END AS attempt
				  FROM
				  (
					  SELECT *
						  ,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
						  ,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS first_attempt
						  ,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt DESC) AS last_attempt
					  FROM
					  (
						  SELECT DISTINCT {6} AS simid ,userid ,logid ,`start` ,`end` AS dt
						  FROM user_sim_log
						  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{4}'
					  ) AS t2_1_1
				  ) AS t2_1_2
				  WHERE (first_attempt = 1 OR (last_attempt = 1 AND first_attempt != 1)) AND start_dt >= "{3}"
				) AS t2_1

				INNER JOIN
				(
				  SELECT simid, TRIM(`name`) AS simname
				  FROM simulation
				  WHERE simid IN ({0})
				) AS t2_2
				ON t2_1.simid = t2_2.simid

				INNER JOIN
				(
				  SELECT t2_3_1.userid
				  FROM
				  (SELECT userid ,groupid FROM user WHERE roleid = 1 {5}) AS t2_3_1
				  {1} JOIN
				  (SELECT groupid FROM user_group {2}) AS t2_3_2
				  ON t2_3_1.groupid = t2_3_2.groupid
				) AS t2_3
				ON t2_1.userid = t2_3.userid

				LEFT JOIN
				(
				  SELECT {6} AS simid ,userid ,logid ,relationid ,`end`
						,CASE
							WHEN relationtype = 1 THEN 3
							WHEN relationtype = 2 THEN 2
							WHEN relationtype = 3 THEN 1
						END AS decision_ord
						,CASE
							WHEN relationtype = 1 THEN "Critical"
							WHEN relationtype = 2 THEN "Suboptimal"
							WHEN relationtype = 3 THEN "Optimal"
						END AS decisiontype
						,{7}
						,{8}
				  FROM user_dialogue_log
				  WHERE simid IN ({0}) AND relationType <= 3 AND relationid IS NOT NULL
				) AS t2_4
				ON t2_1.simid = t2_4.simid AND t2_1.userid = t2_4.userid AND t2_1.logid = t2_4.logid
			)

			SELECT t0_1.* ,t0_2.attempt ,t0_2.total_attempt ,t0_3.decision_level_num ,t0_3.decision_ord ,t0_3.decisiontype ,t0_3.choice_num ,t0_3.n
			FROM
			(
			  SELECT simid ,simname ,COUNT(DISTINCT userid) AS total_sim
			  FROM stats_tbl
			  GROUP BY 1, 2
			) AS t0_1

			LEFT JOIN
			(
			  SELECT simid ,attempt ,COUNT(DISTINCT userid) AS total_attempt
			  FROM stats_tbl
			  GROUP BY 1, 2
			) AS t0_2
			ON t0_1.simid = t0_2.simid

			LEFT JOIN
			(
			  SELECT simid ,attempt ,decision_level_num ,decision_ord ,decisiontype ,choice_num ,COUNT(DISTINCT userid) AS n
			  FROM stats_tbl
			  WHERE dec_num = 1
			  GROUP BY 1, 2, 3, 4, 5, 6
			) AS t0_3
			ON t0_2.simid = t0_3.simid AND t0_2.attempt = t0_3.attempt;
			'''.format(
				', '.join([str(x) for x in sim_id]),
				user_groups_merge,
				cmp_user_groups,

				start_date,
				end_date,
				cmp_uid,

				def_simid,

				def_decision_level,
				def_choice
			),
			db_connection
		)




		df_sql_skills = pd.read_sql_query(
			'''
			SELECT simid ,orderid ,REPLACE(TRIM(`label`), '\u200b', '') AS skillname ,hidden
			FROM score
			WHERE simid IN ({0});
			'''.format(
				','.join([str(x) for x in sim_id])
			)
			,db_connection
		)


		if df_sql.shape[0] > 0:

			# Bring in Sim Section, Scenario and Decision Level text
			df_sql = df_sql\
			.merge(
				# Sim Levels
				df_sim_levels\
				.query('performancebranch != 1')\
				.filter(['simid', 'sectionid', 'section', 'decision_level', 'decision_level_num', 'scenario'])\
				.drop_duplicates(),

				how='inner',
				on=['simid', 'decision_level_num']
			)

			# Bring in Choice text
			df_sql = df_sql\
			.merge(
				df_sim_model_levels\
				.filter(['simid', 'sectionid', 'section', 'decision_level', 'decisiontype', 'choice_num', 'choice'])\
				.drop_duplicates(),

				how='left',
				on=['simid', 'sectionid', 'section', 'decision_level', 'decisiontype', 'choice_num']
			)



			# Fill in zeros
			df_summary = df_sql\
			.merge(
				df_sql\
				.filter(['simid', 'simname', 'total_sim', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decision_ord', 'decisiontype', 'choice_num', 'choice'])\
				.drop_duplicates()\
				.merge(
					df_sql\
					.filter(['simid', 'attempt', 'total_attempt'])\
					.drop_duplicates(),

					how='left',
					on=['simid']
				),

				how='right',
				on=['simid', 'simname', 'total_sim', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decision_ord', 'decisiontype', 'choice_num', 'choice', 'attempt', 'total_attempt']
			)\
			.assign(
				n = lambda x: x['n'].apply(lambda y: int(0) if pd.isnull(y) else int(y)),
				total_decision = lambda x: x.groupby(['simid', 'simname', 'attempt', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario'])['n'].transform('sum'),
				pct = lambda x: x.apply(lambda y: 0 if pd.isnull(y['total_decision']) or y['total_decision'] == 0 else (y['n']/y['total_decision'])*100, axis=1),
				rect_height = lambda x: x['total_decision']/x['total_attempt'],

				attempt_n = lambda x: x.apply(lambda y: y['attempt'] + '\n(' + '{:,}'.format(int(y['total_attempt'])) + ' Learners)', axis=1),
				bar_color = lambda x: x['decisiontype'].apply(lambda y: '#339933' if y =='Optimal' else '#ffb833' if y == 'Suboptimal' else '#e32726'),

				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order', 'attempt', 'sectionid', 'decision_level_num', 'decision_level', 'decision_ord', 'decisiontype', 'choice_num', 'choice'])




			# --- Get Coaching and Feedback --->
			df_summary = df_summary\
			.merge(
				df_sim_model_levels\
				.filter(['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num', 'feedback', 'coaching'])\
				.groupby(['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num'])\
				.first()\
				.reset_index(),

				how='left',
				on=['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num']
			)\
			.assign(
				feedback = lambda x: x['feedback'].apply(lambda y: "-" if pd.isnull(y) else y),
				coaching = lambda x: x['coaching'].apply(lambda y: "-" if pd.isnull(y) else y),
			)



			# --- Get Skills --->
			df_skills = df_sim_levels\
			.merge(
				df_xml\
				.merge(
					df_sql_skills\
					.filter(['simid', 'orderid', 'skillname']),

					how='left',
					on=['simid', 'skillname']
				)\
				.assign(
					skillid = lambda x: x.apply(lambda y: y['orderid'] if pd.notnull(y['orderid']) else y['skillid'], axis=1),
					dialogueid = lambda x: x['startingpoint'].apply(lambda y: int(y) if pd.notnull(y) else None)
				),

				how='left',
				on=['simid', 'dialogueid']
			)\
			.sort_values(['simid', 'decision_level_num', 'decision_level', 'skillid', 'skillname'])\
			.filter(['simid', 'decision_level_num', 'decision_level', 'skillid', 'skillname'])\
			.drop_duplicates()

			# Remove hidden skills, if required
			if not show_hidden_skills:
				df_skills = df_skills\
				.merge(
					df_sql_skills\
					.query('hidden != 1')\
					.drop(columns=['hidden', 'orderid']),

					how='inner',
					on=['simid', 'skillname']
				)

			df_skills = df_skills\
			.groupby(['simid', 'decision_level_num', 'decision_level'])\
			['skillname'].apply(list)\
			.reset_index()\
			.rename(columns={'skillname': 'skills'})


			dict_df['sim']['decision_levels'] = df_summary\
			.merge(
				df_skills,

				how='left',
				on=['simid', 'decision_level_num', 'decision_level']
			)

			#list_summary.append(df_summary)

		else:
			dict_df['sim']['decision_levels'] = df_sim_levels\
			.sort_values(['simid', 'sectionid', 'decision_level_num', 'decision_level', 'scenario', 'choice'])\
			.filter(['simid', 'simname', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'choice'])\
			.drop_duplicates()\
			.assign(
				n = 0,
				total_sim = 0,
				total_attempt = 0,
				total_decision = 0,
				pct = 0,

				bar_color = lambda x: x['decisiontype'].apply(lambda y: '#c61110' if y == "Critical"
																else '#f29000' if y == "Suboptimal"
																else '#2aa22a'),

				attempt = lambda x: x.apply(lambda y: 'First Attempt' + '<br>(' + '{:,}'.format(y['total_attempt']) + ' Learners)', axis=1),

				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order', 'simid', 'attempt', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'choice'])

		# <--- Summarize Data ---


	# <--- DECISION LEVELS ---





	# --- BEHAVIORS AND CONSEQUENCES --->

	if behaviors:

		dict_df['sim']['behaviors'] = pd.DataFrame()

		if df_xml.query('behavior.notnull() and consequence.notnull()').shape[0] > 0:

			# Summarize data
			dict_df['sim']['behaviors'] = df_xml\
			.query('behavior.notnull() and consequence.notnull()')\
			.sort_values(['simid', 'behaviorid', 'behavior', 'relationtype', 'decisiontype', 'consequence'])\
			.filter(['simid', 'simname', 'behaviorid', 'behavior', 'relationtype', 'decisiontype', 'consequence'])\
			.drop_duplicates()\
			.merge(
				df_sql_decision_level\
				.rename(columns={'relationType':'relationtype'})\
				.merge(
					df_xml\
					.filter(['relationid', 'behaviorid', 'behavior', 'consequence'])\
					.drop_duplicates(),

					how='inner',
					on=['relationid']
				)\
				.assign(
					total = lambda x: x.groupby(['simid'])['userid'].transform('nunique')
				)\
				.groupby(['simid', 'simname', 'total', 'behaviorid', 'behavior', 'relationtype', 'decisiontype', 'consequence'])\
				.agg(
					n = ('userid', 'nunique')
				)\
				.reset_index()\
				.assign(
					pct = lambda x: (x['n']/x['total'])*100
				),

				how='left',
				on=['simid', 'behaviorid', 'behavior', 'relationtype', 'decisiontype', 'consequence']
			)\
			.assign(
				n = lambda x: x['n'].apply(lambda y: 0 if pd.isnull(y) else y),
				pct = lambda x: x['pct'].apply(lambda y: 0 if pd.isnull(y) else y),
				bar_color = lambda x: x['decisiontype'].apply(lambda y: '#c61110' if y == "Critical"
																else '#f29000' if y == "Suboptimal"
																else '#2aa22a')
			)

	# <--- BEHAVIORS AND CONSEQUENCES ---





	# --- TIME SPENT --->

	if time_spent:

		dict_df['sim']['time_spent'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		dict_sql['sim']['time_spent'] = '''
		SELECT simid ,simname
		  ,CAST(total AS UNSIGNED) AS total
		  ,stat_order ,stat
		  ,bar_color
		  ,n
		  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
		  ,avg_cum_duration
		  ,CASE
			WHEN total > 0 THEN (((((n/total)*100) - 0)/(100 - 0))*(1.0 - 0.1))+0.1
			ELSE 1
		  END AS opac

		FROM
		(
		  SELECT t1.simid ,t1.simname
			,CASE WHEN t1.stat_order IS NOT NULL THEN t1.stat_order ELSE t2.stat_order END AS stat_order
			,CASE
				WHEN t2.stat IS NOT NULL AND t2.n = 1 THEN CONCAT(t2.stat, "<br>(", FORMAT(t2.n, 0), " Learner)")
				WHEN t2.stat IS NOT NULL AND t2.n != 1 THEN CONCAT(t2.stat, "<br>(", FORMAT(t2.n, 0), " Learners)")
				ELSE CONCAT(t1.stat, "<br>(0 Learners)")
			END AS stat
			,CASE WHEN t1.stat_order = 1 THEN "#1f77b4" ELSE "#e32726" END AS bar_color
			,MAX(CASE WHEN t1.stat_order = 1 AND t2.n IS NOT NULL THEN t2.n ELSE 0 END) OVER (PARTITION BY t1.simid) AS total
			,CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END AS n
			,CASE WHEN t2.avg_cum_duration IS NULL THEN 0 ELSE t2.avg_cum_duration END AS avg_cum_duration
		  FROM
		  (
			SELECT *
			FROM
			(
			  SELECT 1 AS stat_order ,"All Attempts" AS stat
			  UNION
			  SELECT 2 AS stat_order ,"1 Attempt" AS stat
			  UNION
			  SELECT 3 AS stat_order ,"2 Attempts" AS stat
			  UNION
			  SELECT 4 AS stat_order ,"3 Attempts" AS stat
			  UNION
			  SELECT 5 AS stat_order ,"4+ Attempts" AS stat
			) AS t1_1,
			(
				SELECT simid, TRIM(`name`) AS simname
				FROM simulation
				WHERE simid IN ({5})
			) AS t1_2
		  ) AS t1

		  LEFT JOIN
		  (
			WITH
			  stats_tbl AS
			  (
				SELECT *
				FROM
				(
				  SELECT t2_1.*
				  FROM
					(
					  SELECT {6} AS simid ,userid ,duration/60 AS duration
						  ,MIN(DATE(`start`)) OVER (PARTITION BY {6}, userid) AS start_dt
						  ,ROW_NUMBER() OVER (PARTITION BY {6}, userid ORDER BY `end`) AS attempt
						  ,SUM(duration/60) OVER (PARTITION BY {6}, userid ORDER BY `end`) AS cum_duration
						  ,ROW_NUMBER() OVER (PARTITION BY {6}, userid ORDER BY `end` DESC) AS last_row
					  FROM user_sim_log
					  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
					) AS t2_1

				  INNER JOIN
					(
					  SELECT t2_3_1.userid
					  FROM
						(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t2_3_1
						{7} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_3_2
						ON t2_3_1.groupid = t2_3_2.groupid
					) AS t2_3
				  ON t2_1.userid = t2_3.userid

				) AS t2_0
				WHERE t2_0.start_dt >= "{2}"
			  )

			  SELECT simid ,1 AS stat_order ,"All Attempts" AS stat ,cnt AS `n` ,AVG(cum_duration) AS avg_cum_duration
			  FROM
			  (
				SELECT *
					,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY cum_duration) AS rown
					,COUNT(*) OVER (PARTITION BY simid) AS cnt
				FROM stats_tbl
				WHERE last_row = 1
			  ) AS stat1
			  WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
			  GROUP BY 1, 2, 3, 4

			  UNION ALL

			  SELECT simid ,2 AS stat_order ,"1 Attempt" AS stat ,cnt AS `n` ,AVG(cum_duration) AS avg_cum_duration
			  FROM
			  (
				SELECT *
					,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY cum_duration) AS rown
					,COUNT(*) OVER (PARTITION BY simid) AS cnt
				FROM stats_tbl
				WHERE attempt = 1
			  ) AS stat2
			  WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
			  GROUP BY 1, 2, 3, 4

			  UNION ALL

			  SELECT simid ,3 AS stat_order ,"2 Attempts" AS stat ,cnt AS `n` ,AVG(cum_duration) AS avg_cum_duration
			  FROM
			  (
				SELECT *
					,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY cum_duration) AS rown
					,COUNT(*) OVER (PARTITION BY simid) AS cnt
				FROM stats_tbl
				WHERE attempt = 2
			  ) AS stat3
			  WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
			  GROUP BY 1, 2, 3, 4

			  UNION ALL

			  SELECT simid ,4 AS stat_order ,"3 Attempts" AS stat ,cnt AS `n` ,AVG(cum_duration) AS avg_cum_duration
			  FROM
			  (
				SELECT *
					,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY cum_duration) AS rown
					,COUNT(*) OVER (PARTITION BY simid) AS cnt
				FROM stats_tbl
				WHERE attempt = 3
			  ) AS stat4
			  WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
			  GROUP BY 1, 2, 3, 4

			  UNION ALL

			  SELECT simid ,5 AS stat_order ,"4+ Attempts" AS stat ,cnt AS `n` ,AVG(cum_duration) AS avg_cum_duration
			  FROM
			  (
				SELECT *
					,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY cum_duration) AS rown
					,COUNT(*) OVER (PARTITION BY simid) AS cnt
				FROM stats_tbl
				WHERE attempt >= 4 AND last_row = 1
			  ) AS stat5
			  WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
			  GROUP BY 1, 2, 3, 4

		  ) AS t2
		  ON t1.simid = t2.simid AND t1.stat_order = t2.stat_order AND t1.stat = t2.stat
		) AS t0
		ORDER BY 1, 4;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,
			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge,
		)

	# <--- TIME SPENT ---





	# --- PRACTICE MODE --->

	if practice_mode:

		dict_df['sim']['practice_mode'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		dict_sql['sim']['practice_mode'] = '''
		SELECT t1.*
			,CASE WHEN t2.total IS NOT NULL THEN CAST(t2.total AS UNSIGNED) ELSE CAST(0 AS UNSIGNED) END AS total
			,CASE WHEN t2.n IS NOT NULL THEN CAST(t2.n AS UNSIGNED) ELSE CAST(0 AS UNSIGNED) END AS n
			,CASE WHEN t2.total > 0 THEN (t2.n/t2.total)*100 ELSE 0 END AS pct
			,t2.avg_practice_duration
		FROM

		(
			SELECT simid, TRIM(`name`) AS simname
			FROM simulation
			WHERE simid IN ({5})
		) AS t1

		LEFT JOIN
		(
			WITH
			stats_tbl AS
			(
				SELECT simid
					,COUNT(*) OVER (PARTITION BY simid) AS total
					,SUM(practice) OVER (PARTITION BY simid) AS n
					,duration
				FROM
				(
					SELECT t2_1.*
						,CASE WHEN t2_4.duration IS NOT NULL THEN 1 ELSE 0 END AS practice
						,t2_4.duration AS duration
					FROM
					(
					  SELECT {6} AS simid ,userid
						  ,MIN(DATE(`start`)) AS start_dt
					  FROM user_sim_log
					  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
					  GROUP BY 1, 2
					) AS t2_1

					INNER JOIN
					(
					  SELECT t2_3_1.userid
					  FROM
						(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t2_3_1
						{7} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_3_2
						ON t2_3_1.groupid = t2_3_2.groupid
					) AS t2_3
					ON t2_1.userid = t2_3.userid

					LEFT JOIN
					(
					  SELECT {6} AS simid, userid ,SUM(duration/60) AS duration
					  FROM explore_sim_log
					  WHERE simid IN ({0})
					  GROUP BY 1, 2
					) AS t2_4
					ON t2_1.simid = t2_4.simid AND t2_1.userid = t2_4.userid

				) AS t2_0_0_0
				WHERE start_dt >= "{2}"
			)

			SELECT t2_0_1.* ,t2_0_2.avg_practice_duration
			FROM
			(
				SELECT DISTINCT simid, total, n
				FROM stats_tbl
			) AS t2_0_1

			LEFT JOIN

			(
				SELECT simid
					,AVG(duration) AS avg_practice_duration
				FROM
				(
					SELECT simid, total, n ,duration
						,COUNT(*) OVER (PARTITION BY simid) AS cnt
						,ROW_NUMBER() OVER (PARTITION BY simid ORDER BY duration) AS rown
					FROM stats_tbl
					WHERE duration IS NOT NULL
				) AS t2_0_2_0
				WHERE rown in ( FLOOR((cnt + 1) / 2), FLOOR( (cnt + 2) / 2) )
				GROUP BY 1
			) AS t2_0_2
			ON t2_0_1.simid = t2_0_2.simid
		) AS t2
		ON t1.simid = t2.simid
		ORDER BY 1;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,

			', '.join([str(x) for x in list_simid]),
			def_simid,

			user_groups_merge,
		)

	# <--- PRACTICE MODE ---





	# --- KNOWLEDGE CHECK --->

	if knowledge_check:

		dict_df['sim']['knowledge_check_1'] = pd.DataFrame()

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		dict_sql['sim']['knowledge_check_1'] = '''
			SELECT simid ,simname ,questionid ,question ,typeid ,optionid ,optiontext AS answer
				,CASE WHEN correct = 1 THEN "Correct" ELSE "Incorrect" END AS answer_type
				,CASE WHEN correct = 1 THEN "#339933" ELSE "#c61110" END AS bar_color
				,CAST(total AS UNSIGNED) AS total
				,n
				,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
			FROM
			(
				SELECT t_1.*
					,SUM(CASE WHEN t_2.n IS NULL THEN 0 ELSE t_2.n END) OVER (PARTITION BY t_1.simid, t_1.questionid) AS total
					,CASE WHEN t_2.n IS NULL THEN 0 ELSE t_2.n END AS n
				FROM
				(
					SELECT t_1_1.simid ,t_1_3.simname ,t_1_1.orderid ,t_1_1.question ,t_1_1.typeid ,t_1_2.optionid ,t_1_2.optiontext ,t_1_2.correct
					FROM
					(
						SELECT * FROM knowledge_question
						WHERE simid IN ({5})
					) AS t_1_1

					LEFT JOIN
					knowledge_option AS t_1_2
					ON t_1_1.questionid = t_1_2.questionid

					INNER JOIN
					(
						SELECT simid ,TRIM(`name`) AS simname
						FROM simulation
						WHERE simid IN ({5})
					) AS t_1_3
					ON t_1_1.simid = t_1_3.simid
				) AS t_1

				LEFT JOIN
				(
					SELECT simid ,orderid ,questionid ,optionid
						,COUNT(*) AS n
					FROM
					(
						SELECT t_2_1.simid ,t_2_1.questionid ,t_2_1.orderid ,t_2_2.optionid ,t_2_4.`end` ,t_2_4.start_dt
							,ROW_NUMBER() OVER (PARTITION BY t_2_1.simid ,t_2_3.simname ,t_2_1.questionid ,t_2_4.userid ORDER BY t_2_4.sim_attempt, t_2_4.question_attempt) AS rown
						FROM

						(
							SELECT *
							FROM knowledge_question
							WHERE simid IN ({0})
						) AS t_2_1

						LEFT JOIN
						knowledge_option AS t_2_2
						ON t_2_1.questionid = t_2_2.questionid

						INNER JOIN
						(
							SELECT simid ,TRIM(`name`) AS simname
							FROM simulation
							WHERE simid IN ({0})
						) AS t_2_3
						ON t_2_1.simid = t_2_3.simid

						LEFT JOIN
						(
							SELECT t_2_4_1.optionid, t_2_4_1.attempt AS question_attempt, t_2_4_2.userid, t_2_4_1.logid ,t_2_4_2.sim_attempt ,t_2_4_2.`end` ,t_2_4_2.start_dt
							FROM
							knowledge_answer AS t_2_4_1

							INNER JOIN
							(
								SELECT userid ,logid ,`end`
									,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY `end`) AS sim_attempt
									,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
								FROM user_sim_log
								WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
							) AS t_2_4_2
							ON t_2_4_1.logid = t_2_4_2.logid

							INNER JOIN
							(
								SELECT t_2_4_3_1.userid
								FROM
								(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t_2_4_3_1
								{7} JOIN
								(SELECT groupid FROM user_group {1}) AS t_2_4_3_2
								ON t_2_4_3_1.groupid = t_2_4_3_2.groupid
							) AS t_2_4_3
							ON t_2_4_2.userid = t_2_4_3.userid
						) AS t_2_4
						ON t_2_2.optionid = t_2_4.optionid
					) AS t_2_0
					WHERE rown = 1 AND start_dt >= "{2}"
					GROUP BY 1, 2, 3, 4
				) AS t_2

				ON t_1.simid = t_2.simid AND t_1.orderid = t_2.orderid
			) AS t_0
			ORDER BY 1, 3, 6;
		'''.format(
			', '.join([str(x) for x in sim_id]),
			cmp_user_groups,
			start_date,
			end_date,
			cmp_uid,
			', '.join([str(x) for x in list_simid]),
			def_simid,
			user_groups_merge,
		)

	# <--- KNOWLEDGE CHECK ---





	# --- SURVEY RESPONSES --->

	if survey:

		dict_df['srv']['survey_responses'] = pd.DataFrame()

		# Create colour variable based on answer type (positive/negative)
		red = [198, 17, 16] #Color("#c61110") #rgb(198, 17, 16)
		light_red = [251, 208, 208] # #fbd0d0 rgb(251, 208, 208)
		white = [255, 255, 255] #Color("#ffffff") #rgb(255, 255, 255)
		green = [42, 162, 42] #Color("#2aa22a") #rgb(42, 162, 42)
		light_green = [214, 245, 214] # #d6f5d6 rgb(214, 245, 214)
		blue = [13, 91, 217] #Color(#0d5bd9) #rgb(13, 91, 217)
		light_blue = [207, 224, 252] #Color(#cfe0fc) #rgb(207, 224, 252)

		cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))

		# Find out which types of Survey questions exist for the Sim (i.e. Yes/No, Multiple Choice, Free-text)
		df_typeid = pd.read_sql_query(
			'''
			SELECT DISTINCT simid, typeid
			FROM quiz_question
			WHERE simid IN ({0});
			'''.format(
				', '.join([str(x) for x in sim_id])
			),
			db_connection
		)

		survey_sql_queries = []

		# Yes/No Questions
		if 1 in list(df_typeid['typeid']):
			print('Yes/No Questions')
			survey_sql_queries.append(
				'''
				SELECT simid ,simname ,orderid ,question ,typeid ,answerid ,answer
					,NULL AS optionvalue
					,CAST(total AS UNSIGNED) AS total
					,CAST(n AS UNSIGNED) AS n
					,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
					,bar_color
					,null AS dt
				FROM
				(
					SELECT t_yn_1.*
						,SUM(CASE WHEN t_yn_2.n IS NULL THEN 0 ELSE t_yn_2.n END) OVER (PARTITION BY t_yn_1.simid, t_yn_1.orderid) AS total
						,CASE WHEN t_yn_2.n IS NULL THEN 0 ELSE t_yn_2.n END AS n
					FROM
					(
						SELECT t_yn_1_1.simid ,t_yn_1_2.simname ,t_yn_1_1.orderid ,t_yn_1_1.question ,t_yn_1_1.typeid ,t_yn_1_1.answerid ,t_yn_1_1.answer ,t_yn_1_1.bar_color
						FROM
						(
							SELECT *
							FROM
							(
								SELECT *
								FROM quiz_question
								WHERE simid IN ({5}) AND typeid = 1
							) AS t_yn_1_1_1,

							(
								SELECT *
								FROM
								(
									SELECT 1 AS answerid ,"Yes" AS answer ,'#2aa22a' AS bar_color
									UNION
									SELECT 2 AS answerid ,"No" AS answer ,'#e32726' AS bar_color
								) AS t_yn_1_1_2_0
							) AS t_yn_1_1_2
						) AS t_yn_1_1

						INNER JOIN
						(
							SELECT simid ,TRIM(`name`) AS simname
							FROM simulation
							WHERE simid IN ({5})
						) AS t_yn_1_2
						ON t_yn_1_1.simid = t_yn_1_2.simid
					) AS t_yn_1

					LEFT JOIN
					(
						SELECT simid ,orderid ,question ,answerid
							,COUNT(*) AS n
						FROM
						(
							SELECT t_yn_2_1.simid ,t_yn_2_1.orderid ,t_yn_2_1.question ,t_yn_2_3.optionid ,t_yn_2_3.answerid ,t_yn_2_3.`end` ,t_yn_2_3.start_dt
								,ROW_NUMBER() OVER (PARTITION BY t_yn_2_1.simid ,t_yn_2_1.orderid ,t_yn_2_1.question ,t_yn_2_3.userid ORDER BY t_yn_2_3.`end`) AS rown
							FROM

							(
								SELECT *
								FROM quiz_question
								WHERE simid IN ({0}) AND typeid = 1
							) AS t_yn_2_1

							INNER JOIN
							(
								SELECT simid ,TRIM(`name`) AS simname
								FROM simulation
								WHERE simid IN ({0})
							) AS t_yn_2_2
							ON t_yn_2_1.simid = t_yn_2_2.simid

							LEFT JOIN
							(
								SELECT t_yn_2_3_1.questionid, t_yn_2_3_1.userid, t_yn_2_3_1.logid ,t_yn_2_3_1.optionid ,t_yn_2_3_3.`end` ,t_yn_2_3_3.start_dt
									,CASE
										WHEN t_yn_2_3_1.yesno = 1 THEN 1
										WHEN t_yn_2_3_1.yesno = 0 THEN 2
									END AS answerid
								FROM

								quiz_answer AS t_yn_2_3_1

								INNER JOIN
								(
									SELECT t_yn_2_3_2_1.userid
									FROM
									(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t_yn_2_3_2_1
									{7} JOIN
									(SELECT groupid FROM user_group {1}) AS t_yn_2_3_2_2
									ON t_yn_2_3_2_1.groupid = t_yn_2_3_2_2.groupid
								) AS t_yn_2_3_2
								ON t_yn_2_3_1.userid = t_yn_2_3_2.userid

								INNER JOIN
								(
									SELECT userid ,logid ,`end`
										,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
									FROM user_sim_log
									WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
								) AS t_yn_2_3_3
								ON t_yn_2_3_1.userid = t_yn_2_3_3.userid AND t_yn_2_3_1.logid = t_yn_2_3_3.logid
							) AS t_yn_2_3
							ON t_yn_2_1.questionid = t_yn_2_3.questionid
						) AS t_yn_2_0
						WHERE rown = 1 AND start_dt >= "{2}"
						GROUP BY 1, 2, 3, 4
					) AS t_yn_2

					ON t_yn_1.simid = t_yn_2.simid AND t_yn_1.orderid = t_yn_2.orderid AND t_yn_1.answerid = t_yn_2.answerid
				) AS t_yn_0
				'''
			)


		# Multiple-Choice Questions (typeid=2)
		# This SQL query extracts all multiple-choice survey question responses, including:
		# - Numeric rating scales (e.g., 1-5, 0-10)
		# - NPS (Net Promoter Score) questions - identified by question text containing "NPS" (see line ~8635)
		# - Agreement scales (Strongly Disagree to Strongly Agree)
		# - Other Likert-type scales
		# The 'optionvalue' field contains the numeric value from quiz_option table (used for calculations)
		if 2 in list(df_typeid['typeid']):
			print('Multiple-Choice Questions')
			survey_sql_queries.append(
				'''
				SELECT simid ,simname ,orderid ,question ,typeid ,answerid ,optiontext AS answer ,value AS optionvalue
					,CAST(total AS UNSIGNED) AS total
					,n
					,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
					,null AS bar_color
					,null AS dt
				FROM
				(
					SELECT t_mc_1.*
						,SUM(CASE WHEN t_mc_2.n IS NULL THEN 0 ELSE t_mc_2.n END) OVER (PARTITION BY t_mc_1.simid, t_mc_1.orderid) AS total
						,CASE WHEN t_mc_2.n IS NULL THEN 0 ELSE t_mc_2.n END AS n
					FROM
					(
						SELECT t_mc_1_1.simid ,t_mc_1_3.simname ,t_mc_1_1.orderid ,t_mc_1_1.question ,t_mc_1_1.typeid ,t_mc_1_2.orderid AS answerid ,t_mc_1_2.optiontext ,t_mc_1_2.value
						FROM
						(
							SELECT *
							FROM quiz_question
							WHERE simid IN ({5}) AND typeid = 2
						) AS t_mc_1_1

						LEFT JOIN
						quiz_option AS t_mc_1_2
						ON t_mc_1_1.questionid = t_mc_1_2.questionid

						INNER JOIN
						(
							SELECT simid ,TRIM(`name`) AS simname
							FROM simulation
							WHERE simid IN ({5})
						) AS t_mc_1_3
						ON t_mc_1_1.simid = t_mc_1_3.simid
					) AS t_mc_1

					LEFT JOIN
					(
						SELECT simid ,orderid ,question ,answerid ,optiontext ,value
							,COUNT(*) AS n
						FROM
						(
							SELECT t_mc_2_1.simid ,t_mc_2_1.orderid ,t_mc_2_1.question ,t_mc_2_1.typeid ,t_mc_2_2.orderid AS answerid ,t_mc_2_2.optiontext ,t_mc_2_2.value ,t_mc_2_4.`end` ,t_mc_2_4.start_dt
								,ROW_NUMBER() OVER (PARTITION BY t_mc_2_1.simid ,t_mc_2_1.orderid ,t_mc_2_1.question ,t_mc_2_4.userid ORDER BY t_mc_2_4.`end`) AS rown
							FROM

							(
								SELECT {6} AS simid ,questionid ,orderid ,question ,typeid
								FROM quiz_question
								WHERE simid IN ({0}) AND typeid = 2
							) AS t_mc_2_1

							LEFT JOIN
							quiz_option AS t_mc_2_2
							ON t_mc_2_1.questionid = t_mc_2_2.questionid

							LEFT JOIN
							(
								SELECT t_mc_2_4_1.questionid, t_mc_2_4_1.optionid, t_mc_2_4_1.userid, t_mc_2_4_1.logid ,t_mc_2_4_3.`end` ,t_mc_2_4_3.start_dt
								FROM
								quiz_answer AS t_mc_2_4_1

								INNER JOIN
								(
									SELECT t_mc_2_4_2_1.userid
									FROM
									(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t_mc_2_4_2_1
									{7} JOIN
									(SELECT groupid FROM user_group {1}) AS t_mc_2_4_2_2
									ON t_mc_2_4_2_1.groupid = t_mc_2_4_2_2.groupid
								) AS t_mc_2_4_2
								ON t_mc_2_4_1.userid = t_mc_2_4_2.userid

								INNER JOIN
								(
									SELECT userid ,logid ,`end`
										,MIN(DATE(`start`)) OVER (PARTITION BY {6} ,userid) AS start_dt
									FROM user_sim_log
									WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
								) AS t_mc_2_4_3
								ON t_mc_2_4_1.userid = t_mc_2_4_3.userid AND t_mc_2_4_1.logid = t_mc_2_4_3.logid
							) AS t_mc_2_4
							ON t_mc_2_2.questionid = t_mc_2_4.questionid AND t_mc_2_2.optionid = t_mc_2_4.optionid
						) AS t_mc_2_0
						WHERE rown = 1 AND start_dt >= "{2}"
						GROUP BY 1, 2, 3, 4, 5, 6
					) AS t_mc_2

					ON t_mc_1.simid = t_mc_2.simid AND t_mc_1.orderid = t_mc_2.orderid AND t_mc_1.answerid = t_mc_2.answerid
				) AS t_mc_0
				'''
			)

		# Free-Text Questions
		if show_survey_comments and 4 in list(df_typeid['typeid']):
			print('Free-Text Questions')

			survey_comments = '''
				SELECT simid ,simname
					,orderid ,question ,typeid
					,0 AS answerid
					,CASE WHEN answer IS NULL THEN "No Responses" ELSE answer END AS answer
					,NULL AS optionvalue
					,total
					,null AS n
					,null AS pct
					,null AS bar_color
					,`end` AS dt
				FROM
				(
					SELECT *
						,ROW_NUMBER() OVER (PARTITION BY t_ft_0_1.simid ,t_ft_0_1.orderid ORDER BY t_ft_0_1.`end` DESC) AS answern
						,COUNT(t_ft_0_1.userid) OVER (PARTITION BY t_ft_0_1.simid, t_ft_0_1.orderid) AS total
					FROM
					(
						SELECT t_ft_1.simid ,t_ft_3.simname ,t_ft_1.orderid ,t_ft_1.question ,t_ft_1.typeid ,t_ft_4.answer ,t_ft_4.userid ,t_ft_4.`end` ,t_ft_4.start_dt
							,ROW_NUMBER() OVER (PARTITION BY t_ft_1.simid ,t_ft_3.simname ,t_ft_1.orderid ,t_ft_1.question ,t_ft_4.userid ORDER BY t_ft_4.`end`) AS rown
						FROM

						(
							SELECT {6} AS simid ,orderid ,questionid ,question ,typeid
							FROM quiz_question
							WHERE simid IN ({0}) AND typeid = 4
						) AS t_ft_1

						INNER JOIN
						(
							SELECT simid ,TRIM(`name`) AS simname
							FROM simulation
							WHERE simid IN ({5})
						) AS t_ft_3
						ON t_ft_1.simid = t_ft_3.simid

						LEFT JOIN
						(
							SELECT t_ft_4_1.questionid, TRIM(t_ft_4_1.answer) AS answer, t_ft_4_1.userid, t_ft_4_1.logid ,t_ft_4_3.`end` ,t_ft_4_3.start_dt
							FROM

							(
								SELECT *
								FROM quiz_answer
								WHERE answer IS NOT NULL AND TRIM(answer) != "" AND answer REGEXP "[[:alnum:]]" AND LENGTH(TRIM(answer)) >= 4
								AND questionid in (SELECT questionid FROM quiz_question WHERE simid IN ({0}) AND typeid = 4)
							) AS t_ft_4_1

							INNER JOIN
							(
								SELECT t_ft_2_3_1.userid
								FROM
								(SELECT userid ,groupid FROM user where roleid = 1 {4}) AS t_ft_2_3_1
								{7} JOIN
								(SELECT groupid FROM user_group {1}) AS t_ft_2_3_2
								ON t_ft_2_3_1.groupid = t_ft_2_3_2.groupid
							) AS t_ft_4_2
							ON t_ft_4_1.userid = t_ft_4_2.userid

							INNER JOIN
							(
								SELECT userid ,logid ,`end`
									,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
								FROM user_sim_log
								WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
							) AS t_ft_4_3
							ON t_ft_4_1.userid = t_ft_4_3.userid AND t_ft_4_1.logid = t_ft_4_3.logid
						) AS t_ft_4
						ON t_ft_1.questionid = t_ft_4.questionid
					) AS t_ft_0_1
					WHERE rown = 1 AND start_dt >= "{2}"
				) AS t_ft_0
				'''

			if survey_comment_limit is not None:
				survey_comments += '''
				WHERE answern <= {0}
				'''.format(str(survey_comment_limit))

			survey_sql_queries.append(survey_comments)


		# Construct the SQL query
		if len(survey_sql_queries) > 0:
			dict_sql['srv']['survey_responses'] = 'SELECT * FROM (' + ' UNION ALL '.join(survey_sql_queries).format(
				', '.join([str(x) for x in sim_id]),
				cmp_user_groups,
				start_date,
				end_date,
				cmp_uid,

				', '.join([str(x) for x in list_simid]),
				def_simid,

				user_groups_merge
			) + ') AS t_all ORDER BY simid ,orderid ,answerid ,dt DESC;'

	# <--- SURVEY RESPONSES ---





	# --- EXTRACT DATA FROM DATABASE --->
	print('Extracting data from mySQL')
	for key1 in dict_sql:
		for key2 in dict_sql[key1]:
			print('## Extracting: ', key1, '##', key2)
			dict_df[key1][key2] = pd.read_sql_query(dict_sql[key1][key2], db_connection)
			#print('##', key1, '##', key2, 'extraced')





	if survey:

		# ====================================================================
		# --- Define Color Scales for Survey Responses --->
		# ====================================================================
		# This section assigns semantic colors to multiple-choice survey questions (typeid=2)
		# based on the meaning of answer options (e.g., negative=red, positive=green)
		#
		# OVERVIEW OF DATA FLOW FOR PLOTTING:
		# 1. SQL Query (lines 4080-4180): Extracts survey data from database
		#    - Retrieves question text, answer options, and response counts
		#    - Filters by: simid, typeid=2, user groups, date range, completion status
		#    - Includes 'optionvalue' field from quiz_option table (numeric values for calculations)
		#
		# 2. Color Assignment (lines 4298-4550): Assigns colors based on semantic meaning
		#    - Numeric scales (including NPS): Red → White → Green gradients
		#    - Agreement scales: Red (disagree) → Green (agree)
		#    - Other semantic scales: Appropriate color gradients
		#    - Non-semantic questions: Blue gradient (neutral)
		#
		# 3. NPS Detection (line ~8635 in JavaScript): Questions with "NPS" in question text
		#    - NPS Score calculated client-side using optionvalue field
		#    - Formula: % Promoters (9-10) - % Detractors (0-6)
		#    - Displayed as donut chart with inner text showing avg_nps_score
		#
		# 4. Plotting (lines 8630+): JavaScript renders charts with assigned colors
		# ====================================================================
		if 2 in list(df_typeid['typeid']):
			print('Survey Colours')
			# Extract only multiple-choice questions (typeid=2) from survey responses
			df_mc_questions = dict_df['srv']['survey_responses'].query('typeid == 2')

			if df_mc_questions.shape[0] > 0:

				list_clr = []

				# Loop through each simulation
				for sim in df_mc_questions['simid'].unique():

					# Loop through each question within the simulation
					for q in df_mc_questions.query('simid == @sim')['orderid'].unique():

						# Get all answer options for this specific question
						q_id = df_mc_questions.query('simid == @sim and orderid == @q', engine='python').filter(['simid', 'orderid', 'answerid', 'answer'])

						question_type = 'scale'

						# ===== NUMERIC SCALE DETECTION =====
						# Detects numeric scales (e.g., 0-10 rating scales, including NPS questions)
						# NPS questions are identified later in JavaScript (line ~8635) by checking if question text contains "NPS"
						# The NPS score calculation happens client-side using the 'optionvalue' field from quiz_option table
						if all([bool(re.search(r'\d', x)) for x in q_id['answer'].to_list()]) and any([bool(not re.search('[a-zA-Z]', x)) for x in q_id['answer'].to_list()]):

							# An odd number of categories will be either red-white-green or green-white-red
							# (e.g., 1-5 scale, 0-10 NPS scale = 11 options)
							if (len(q_id['answer'].to_list())%2) > 0:
								# Categories ordered smallest to biggest (e.g., 0,1,2,3,4,5,6,7,8,9,10)
								# Color: Red (low/negative) → White (neutral) → Green (high/positive)
								if [int(re.findall(r'\d+', x)[0]) for x in q_id['answer'].to_list()] == sorted([int(re.findall(r'\d+', x)[0]) for x in q_id['answer'].to_list()]):
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# Categories ordered biggest to smallest (e.g., 10,9,8,7,6,5,4,3,2,1,0)
								# Color: Green (high/positive) → White (neutral) → Red (low/negative)
								else:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

							# An even number of categories will be either red-white-green or green-white-red
							# (e.g., 1-4 scale, 1-6 scale)
							else:
								# Categories ordered smallest to biggest
								# Color: Red (low/negative) → White (neutral) → Green (high/positive)
								if [int(re.findall(r'\d+', x)[0]) for x in q_id['answer'].to_list()] == sorted([int(re.findall(r'\d+', x)[0]) for x in q_id['answer'].to_list()]):
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2)+1)[1:]

								# Categories ordered biggest to smallest
								# Color: Green (high/positive) → White (neutral) → Red (low/negative)
								else:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2)+1)[1:]



						# ===== AGREE/DISAGREE SCALE =====
						# Detects agreement scales (supports English "AGREE" and Spanish "ACUERDO")
						elif any([re.findall('|'.join(["AGREE", "ACUERDO"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							# Check if negative response ("Disagree") is in the first category
							# If yes, color scheme is: Red (disagree) → Green (agree)
							if re.findall('|'.join(["NOT AGREE", "DISAGREE", "DESACUERDO"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# Odd number: Red → White → Green (e.g., Strongly Disagree, Disagree, Neutral, Agree, Strongly Agree)
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# Even number: Red → Light Red → Light Green → Green (e.g., Strongly Disagree, Disagree, Agree, Strongly Agree)
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))


							# Positive response ("Agree") is in the first category
							# Color scheme is: Green (agree) → Red (disagree)
							else:
								# Odd number: Green → White → Red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# Even number: Green → Light Green → Light Red → Red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))



						# ===== OTHER SEMANTIC SCALES =====
						# The following scales follow the same logic as Agree/Disagree:
						# - Detect scale type by keyword (CLEAR, EASY, RELEVANT, VALUABLE, LIKELY)
						# - Check if negative option is first or last
						# - Apply Red (negative) → Green (positive) or reverse

						# Very clear/Very unclear
						elif any([re.findall('|'.join(["CLEAR"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							print("CLEAR/UNCLEAR")
							# "Unclear" is in the first Category
							if re.findall('|'.join(["NOT CLEAR", "UNCLEAR"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# An odd number of categories will be red-white-green
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be red-green
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))

							# Categories ordered GREEN to RED
							else:
								# An odd number of categories will be green-white-red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be  green-red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))



						# Easy/Difficult Scale
						elif any([re.findall('|'.join(["EASY", "DIFFICULT", "HARD"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							# "Difficult" is in the first Category
							if re.findall('|'.join(["DIFFICULT", "HARD", "NOT EASY"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# An odd number of categories will be red-white-green
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be red-green
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))

							# Categories ordered GREEN to RED
							else:
								# An odd number of categories will be green-white-red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be  green-red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))



						# Very Relevant/Not Relevant Scale
						elif any([re.findall('|'.join(["RELEVANT"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							# "Not Relevant" is in the first Category
							if re.findall('|'.join(["NOT RELEVANT", "IRRELEVANT"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# An odd number of categories will be red-white-green
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be red-green
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))

							# Categories ordered GREEN to RED
							else:
								# An odd number of categories will be green-white-red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be  green-red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))



						# Valuable/Not Valuable
						elif any([re.findall('|'.join(["VALUABLE"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							# "Not Valuable" is in the first Category
							if re.findall('|'.join(["NOT VALUABLE", "UNVALUABLE"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# An odd number of categories will be red-white-green
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be red-green
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))

							# Categories ordered GREEN to RED
							else:
								# An odd number of categories will be green-white-red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be  green-red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))



						# Likely/Not Likely
						elif any([re.findall('|'.join(["LIKELY"]), x.upper(), re.IGNORECASE) for x in q_id['answer'].to_list()]):
							# "Not Valuable" is in the first Category
							if re.findall('|'.join(["NOT LIKELY", "UNLIKELY"]), q_id['answer'].to_list()[0].upper(), re.IGNORECASE):
								# An odd number of categories will be red-white-green
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(red, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, green, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be red-green
								else:
									clr_list = rgb_scale(red, light_red, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_green, green, int(len(q_id['answer'].to_list())/2))

							# Categories ordered GREEN to RED
							else:
								# An odd number of categories will be green-white-red
								if (len(q_id['answer'].to_list())%2) > 0:
									clr_list = rgb_scale(green, white, math.ceil(len(q_id['answer'].to_list())/2)) + rgb_scale(white, red, math.ceil(len(q_id['answer'].to_list())/2))[1:]

								# An even number of categories will be  green-red
								else:
									clr_list = rgb_scale(green, light_green, int(len(q_id['answer'].to_list())/2)) + rgb_scale(light_red, red, int(len(q_id['answer'].to_list())/2))




						# ===== NO SEMANTIC SCALE DETECTED =====
						# For questions that don't fit any of the above patterns (e.g., categorical choices)
						# Assign neutral blue gradient colors
						else:
							question_type = 'not scale'
							#clr_list = ['#4285f4']*len(q_id['answer'].to_list())
							clr_list = rgb_scale(blue, light_blue, len(q_id['answer'].to_list()))

						# Replicate question_type for each answer option
						question_type = [question_type]*len(q_id['answer'].to_list())

						# Add the color assignments and scale type to the list
						list_clr.append(
							q_id\
							.assign(
								bar_color = clr_list,
								scale_type = question_type
							)
						)

				# Combine all color assignments into a single dataframe
				df_clr = pd.concat(list_clr, ignore_index=True)


				# Merge the color assignments back to the original multiple-choice questions data
				# This adds 'bar_color' and 'scale_type' columns to each answer option
				df_mc_questions = df_mc_questions\
				.drop(columns=['bar_color'])\
				.merge(
					df_clr,

					how='left',
					on=['simid', 'orderid', 'answerid', 'answer']
				)


			# Rebuild the complete survey_responses dataset:
			# 1. Keep all non-multiple-choice questions (typeid != 2) with original data
			# 2. Add the updated multiple-choice questions (typeid = 2) with new color assignments
			# 3. Sort by simulation, question order, answer order, and date (most recent first)
			dict_df['srv']['survey_responses'] = pd.concat([
				dict_df['srv']['survey_responses']\
				.query('typeid != 2'),

				df_mc_questions
			], ignore_index=True)\
			.sort_values(['simid', 'orderid', 'answerid', 'dt'], ascending=[True, True, True, False])

		# <--- Define Color Scales for Survey Responses ---


		# --- Comment Topic analysis --->

		if survey_topic_analysis and 4 in list(df_typeid['typeid']) and show_survey_comments:

			list_topic = []
			list_no_topic = []

			print('### Topic Analyses')

			for q_i, q_row in dict_df['srv']['survey_responses'].query('typeid == 4').filter(['simid', 'simname', 'orderid', 'question', 'typeid', 'total']).drop_duplicates().iterrows():

				if dict_df['srv']['survey_responses'].query('simid == ' + str(q_row['simid']) + ' and orderid == ' + str(q_row['orderid'])).shape[0] > 100:
					print('Topic Analysis for', '{:,}'.format(dict_df['srv']['survey_responses'].query('simid == ' + str(q_row['simid']) + ' and orderid == ' + str(q_row['orderid'])).shape[0]), 'comments')

					docs = dict_df['srv']['survey_responses'].query('simid == ' + str(q_row['simid']) + ' and orderid == ' + str(q_row['orderid']))['answer']

					# Fine-tune your topic representations
					representation_model = KeyBERTInspired()
					topic_model = BERTopic(representation_model=representation_model)

					topics, probs = topic_model.fit_transform(docs)

					# Reduce number of topics to a maximum of 50
					#topic_model.reduce_topics(docs, nr_topics=50)
					#topics = topic_model.topics_

					list_topic.append(
						topic_model.get_document_info(docs)\
						.query('Topic >= 0 and Topic <= 49')\
						.merge(
							topic_model.get_topic_info()\
							.assign(
								topic_keywords = lambda x: x['Representation'].apply(lambda y: ', '.join([z for z in y if z is not None and z != ""])),
								Count = lambda x: x.groupby(['topic_keywords'])['Count'].transform('sum'),
							)\
							.filter(['Topic', 'topic_keywords', 'Count'])\
							.merge(
								topic_model.get_topic_info()\
								.assign(
									topic_keywords = lambda x: x['Representation'].apply(lambda y: ', '.join([z for z in y if z is not None and z != ""])),
									Count = lambda x: x.groupby(['topic_keywords'])['Count'].transform('sum'),
								)\
								.filter(['topic_keywords', 'Count'])\
								.drop_duplicates()\
								.sort_values(['Count'], ascending=False)
								.reset_index(drop=True)\
								.assign(
									answerid = lambda x: x.index+1
								)\
								.filter(['topic_keywords', 'answerid']),

								how='left',
								on=['topic_keywords']
							),

							how='left',
							on=['Topic']
						)\
						.sort_values(['answerid', 'Probability'], ascending=[True, False])\
						.filter(['answerid', 'topic_keywords', 'Document', 'Count'])\
						.rename(columns={'Document':'answer', 'Count':'n'})\
						.assign(
							optionvalue = lambda x: x.groupby(['answerid'])['answer'].cumcount()+1
						)\
						.query('optionvalue <= 20')\
						.assign(
							simid = q_row['simid'],
							simname = q_row['simname'],
							orderid = q_row['orderid'],
							question = q_row['question'],
							typeid = q_row['typeid'],
							total = q_row['total'],
							pct = lambda x: (x['n']/x['total'])*100,
							bar_color = '#e32726',
							topic_analysis = 1
						)
					)

				else:
					list_no_topic.append({
						'simid': q_row['simid'],
						'orderid': q_row['orderid']
					})



			if len(list_topic) > 0 and len(list_no_topic) > 0:
				df_topic = pd.concat([
					pd.concat(list_topic)\
					.assign(
						topic_analysis = 1
					),

					dict_df['srv']['survey_responses']\
					.query('typeid == 4')\
					.merge(
						pd.DataFrame(list_no_topic),

						how='inner',
						on=['simid', 'orderid']
					)\
					.assign(
						topic_analysis = 0
					)

				], ignore_index=True)

			elif len(list_topic) > 0 and len(list_no_topic) == 0:
				df_topic = pd.concat(list_topic)\
				.assign(
					topic_analysis = 1
				)

			else:
				df_topic = dict_df['srv']['survey_responses']\
				.query('typeid == 4')\
				.merge(
					pd.DataFrame(list_no_topic),

					how='inner',
					on=['simid', 'orderid']
				)\
				.assign(
					topic_analysis = 0
				)


			dict_df['srv']['survey_responses'] = pd.concat([
				dict_df['srv']['survey_responses']\
				.query('typeid != 4'),

				df_topic
			], ignore_index=True)\
			.sort_values(['simid', 'orderid', 'answerid', 'dt', 'optionvalue'], ascending=[True, True, True, False, True])

	# <--- Comment Topic analysis ---












	# ################################
	# ##### PROJECT SUMMARY DATA #####
	# ################################

	if dict_project is not None:
		print('Project/Course Summary data')

		# Convert many-to-one dictionary to a more correct version
		dict_project_alt = {}
		for k, v in dict_project.items():
			if isinstance(k, int):
				dict_project_alt[k] = v
			else:
				for key in list(k):
					dict_project_alt[key] = v


		project_var = '''
		CASE
		'''

		for key, value in dict_project.items():
			if isinstance(key, int):
				project_var += '''
				WHEN simid IN ({0}) THEN "{1}"
				'''.format(str(key), dict_project[key])

			else:
				project_var += '''
				WHEN simid IN ({0}) THEN "{1}"
				'''.format(",".join([str(x) for x in key]), dict_project[key])

		project_var += '''
		END AS project
		'''



		print('## Extracting: ', 'proj', '##', 'proj_sims')

		dict_df['proj']['proj_sims'] = pd.read_sql_query('''
				SELECT {2} ,simid, TRIM(`name`) AS simname
				,{1}
				FROM simulation
				WHERE simid IN ({0})
				ORDER BY 4, 1;
			'''.format(
				', '.join([str(x) for x in list_simid]),
				project_var,
				def_sim_order
			),
			db_connection
		)


		# Add project variable to all other datasets
		for key1 in dict_df:
			if key1 in ['sim', 'srv', 'dmg']:
				for key2 in dict_df[key1]:
					if 'simid' in dict_df[key1][key2].columns:
						dict_df[key1][key2] = dict_df[key1][key2]\
						.assign(
							project = lambda x: x['simid'].apply(lambda y: dict_project_alt.get(y) if pd.notnull(y) else None)
						)



		if learner_engagement:

			print('## Extracting: ', 'proj', '##', 'proj_engagement')

			df_proj_engagement = pd.read_sql_query('''
				SELECT t1.project
					,CASE WHEN t2.total IS NULL THEN 0 ELSE t2.total END AS total
					,CASE WHEN t2.total_all_complete IS NULL THEN 0 ELSE t2.total_all_complete END AS total_all_complete
					,CASE WHEN t2.pct_all_complete IS NULL THEN 0 ELSE t2.pct_all_complete END AS pct_all_complete
				FROM
				(
					SELECT DISTINCT {4}
					FROM simulation
					WHERE simid IN ({7})
				) AS t1

				LEFT JOIN
				(
					WITH stats_tbl
					AS
					(
						SELECT DISTINCT t2_1.project ,t2_1.simid ,t2_1.userid
						FROM
						(
							SELECT {8} AS simid ,userid ,complete
							,MIN(DATE(`start`)) OVER (PARTITION BY {8} ,userid) AS start_dt
							,{4}
							FROM user_sim_log
							WHERE simid IN ({0}) AND complete = 1  AND DATE(`end`) <= '{3}'
						) AS t2_1

						INNER JOIN
						(
							SELECT t2_3_1.userid
							FROM
							(SELECT userid ,groupid FROM user where roleid = 1 {6}) AS t2_3_1
							{9} JOIN
							(SELECT groupid FROM user_group {1}) AS t2_3_2
							ON t2_3_1.groupid = t2_3_2.groupid
						) AS t2_3
						ON t2_1.userid = t2_3.userid
						WHERE t2_1.start_dt >= "{2}"
					)

					SELECT t2_0_1.project ,t2_0_1.total ,t2_0_2.total_all_complete
						,CASE WHEN t2_0_2.total_all_complete IS NOT NULL AND t2_0_1.total != 0 THEN (t2_0_2.total_all_complete/t2_0_1.total)*100 ELSE 0 END AS pct_all_complete
					FROM
					(
						SELECT project ,COUNT(DISTINCT userid) AS total
						FROM stats_tbl
						GROUP BY 1
					) AS t2_0_1

					LEFT JOIN
					(
						SELECT t2_0_2_1.project, COUNT(DISTINCT t2_0_2_1.userid) AS total_all_complete
						FROM
						(
							SELECT project ,userid ,COUNT(DISTINCT simid) AS n_sims_complete
							FROM stats_tbl
							GROUP BY 1, 2
						) AS t2_0_2_1
						INNER JOIN
						(
							SELECT {4}, COUNT(DISTINCT simid) AS n_sims_in_project
							FROM simulation
							WHERE simid IN ({7})
							GROUP BY 1
						) AS t2_0_2_2
						ON t2_0_2_1.project = t2_0_2_2.project
						WHERE t2_0_2_1.n_sims_complete = t2_0_2_2.n_sims_in_project
						GROUP BY 1
					) AS t2_0_2
					ON t2_0_1.project = t2_0_2.project
				) AS t2
				ON t1.project = t2.project;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					cmp_user_groups,
					start_date,
					end_date,
					project_var,
					len(list_simid),
					cmp_uid,
					', '.join([str(x) for x in list_simid]),
					def_simid,

					user_groups_merge,
				),
				db_connection
			)


			dict_df['proj']['proj_engagement'] = df_proj_engagement\
			.merge(
				dict_df['sim']['learner_engagement']\
				.query('stat_order == 2')\
				.filter(['project', 'simid', 'simname', 'stat_order', 'stat', 'bar_color', 'n']),

				how='inner',
				on=['project']
			)\
			.assign(
				pct = lambda x: (x['n']/x['total'])*100,
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order'])





		if learner_engagement_over_time:

			print('## Extracting: ', 'proj', '##', 'proj_engagement_over_time')

			dict_df['proj']['proj_engagement_over_time'] = pd.read_sql_query('''
				SELECT project
				  ,MAX(complete_any_sim) OVER (PARTITION BY project) AS complete_any_sim
				  ,simid ,simname
				  ,"{10}" AS time_freq
				  ,dt
				  ,{11} AS dt_char
				  ,'#4285f4' AS bar_color
				  ,CAST(total AS UNSIGNED) AS total
				  ,n
				  ,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
				  ,n_cum
				FROM
				(
				  SELECT t1.*
					,CASE WHEN t2.complete_any_sim IS NOT NULL THEN t2.complete_any_sim ELSE 0 END AS complete_any_sim
					,SUM(CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END) OVER (PARTITION BY t1.simid) AS total
					,CASE WHEN t2.n IS NOT NULL THEN t2.n ELSE 0 END AS n
					,SUM(CASE WHEN t2.n IS NOT NULL THEN t2.n ELSE 0 END) OVER (PARTITION BY t1.simid ORDER BY t1.dt) AS n_cum
				  FROM
				  (
					SELECT *
					FROM
					(
					  SELECT {4} ,simid, TRIM(`name`) AS simname
					  FROM simulation
					  WHERE simid IN ({7})
					) AS t1_1,
					(
					  SELECT
						  DISTINCT {12} AS dt
					  FROM
					  (
						  SELECT ADDDATE('1970-01-01',t4.i*10000 + t3.i*1000 + t2.i*100 + t1.i*10 + t0.i) AS dt
						  FROM
						   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t0,
						   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t1,
						   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t2,
						   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t3,
						   (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t4
					  ) AS t1_2_0
					  WHERE dt BETWEEN '{2}' AND '{3}'
					) AS t1_2
				  ) AS t1

				  LEFT JOIN
				  (
					WITH
					  stats_tbl AS
					(
					  SELECT *
					  FROM
					  (
						  SELECT t2_1.simid ,t2_1.userid ,t2_1.start_dt
							,MIN(t2_1.dt) AS dt
						  FROM
							(
							  SELECT {8} AS simid ,userid ,complete ,DATE(`end`) AS dt
								,MIN(DATE(`start`)) OVER (PARTITION BY {8} ,userid) AS start_dt
							  FROM user_sim_log
							  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
							) AS t2_1

						  INNER JOIN
							(
							  SELECT t2_2_1.userid
							  FROM
								(SELECT userid ,groupid FROM user WHERE roleid = 1 {6}) AS t2_2_1
								{9} JOIN
								(SELECT groupid FROM user_group {1}) AS t2_2_2
								ON t2_2_1.groupid = t2_2_2.groupid
							) AS t2_2
						  ON t2_1.userid = t2_2.userid

						  GROUP BY 1, 2, 3
					  ) AS t2_0
					  WHERE start_dt >= "{2}"
					)

					SELECT t2_0_1.project, t2_0_1.complete_any_sim ,t2_0_2.simid ,t2_0_2.dt ,t2_0_2.n
					FROM
					(
						SELECT {4} ,COUNT(DISTINCT userid) AS complete_any_sim
						FROM stats_tbl
						GROUP BY 1
					) AS t2_0_1
					LEFT JOIN
					(
						SELECT {4} ,simid
						  ,{12} AS dt
						  ,COUNT(DISTINCT userid) AS `n`
						FROM stats_tbl
						GROUP BY 1, 2, 3
					) AS t2_0_2
					ON t2_0_1.project = t2_0_2.project
				  ) AS t2

				  ON t1.project = t2.project AND t1.simid = t2.simid AND t1.dt = t2.dt
				) AS t0
				ORDER BY 6, 1;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					cmp_user_groups,
					start_date,
					end_date,
					project_var,
					len(list_simid),
					cmp_uid,

					', '.join([str(x) for x in list_simid]),
					def_simid,

					user_groups_merge,

					time_freq,
					date_format,
					date_calculation
				),
				db_connection
			)\
			.assign(
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['project', 'dt', 'sim_order'])





		if overall_pass_rates:

			print('## Extracting: ', 'proj', '##', 'proj_overall_pass_rates')

			dict_df['proj']['proj_overall_pass_rates'] = dict_df['sim']['overall_pass_rates']\
			.assign(
				total_pass_rate = lambda x: x.groupby(['project', 'simid'])['pct'].transform('sum'),
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order'])





		if skill_pass_rates:

			print('## Extracting: ', 'proj', '##', 'proj_skill_pass_rates')

			dict_df['proj']['proj_skill_pass_rates'] = dict_df['sim']['skill_pass_rates']\
			.assign(
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order'])





		if time_spent:

			print('## Extracting: ', 'proj', '##', 'proj_time_spent')

			dict_df['proj']['proj_time_spent'] = dict_df['sim']['time_spent']\
			.query('stat_order == 1')\
			.assign(
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order'])


		if practice_mode:

			print('## Extracting: ', 'proj', '##', 'proj_practice_mode')

			dict_df['proj']['proj_practice_mode'] = dict_df['sim']['practice_mode']\
			.assign(
				sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
			)\
			.sort_values(['sim_order'])








	# ####################################
	# ##### DEMOGRAPHICS ANALYSES V2 #####
	# ####################################

	if df_demog is not None:
		print('Demographic Analyses - V2')

		list_demog_var_vals = []
		for demog_var in [x for x in df_demog.columns if x != 'uid' and '_ord' not in x]:
			sort_ord = '_ord' if (demog_var + '_ord') in df_demog.columns else ''
			for demog_val in df_demog.sort_values([demog_var + sort_ord])[demog_var].unique():
				list_demog_var_vals.append(pd.DataFrame({'demog_var': [demog_var], 'demog_val': [demog_val]}))

		dict_df['dmg']['dmg_vars'] = pd.concat(list_demog_var_vals, ignore_index=True)




		if learner_engagement:

			df_demog_engagement = pd.read_sql_query('''
					SELECT t1.* ,t2.userid ,t2.uid
					FROM
					(
					  SELECT *
					  FROM
					  (
						SELECT 1 AS stat_order ,"Not Completed" AS stat ,'#d3d2d2' AS bar_color
						UNION
						SELECT 2 AS stat_order ,"Completed" AS stat ,'#4285f4' AS bar_color
					) AS t1_1,
					(
						SELECT simid, TRIM(`name`) AS simname
						FROM simulation
						WHERE simid IN ({5})
					) AS t1_2
					) AS t1

					LEFT JOIN
					(
					  WITH
						stats_tbl AS
						(
						  SELECT *
						  FROM
						  (
							SELECT t2_1.simid ,t2_1.userid ,t2_2.uid ,t2_1.start_dt
							  ,SUM(t2_1.complete) AS n_complete
							  ,MAX(t2_1.dt) AS dt
							FROM
							  (
								SELECT {6} AS simid ,userid ,complete
									,CASE WHEN complete = 1 THEN `end` ELSE `start` END AS dt
									,MIN(DATE(`start`)) OVER (PARTITION BY {6} ,userid) AS start_dt
								FROM user_sim_log
								WHERE simid IN ({0}) AND CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}'
							  ) AS t2_1

							INNER JOIN
							  (
								SELECT t2_2_1.userid ,t2_2_1.uid
								FROM
								  (SELECT userid ,uid ,groupid FROM user WHERE roleid = 1 {4}) AS t2_2_1
								  {7} JOIN
								  (SELECT groupid FROM user_group {1}) AS t2_2_2
								  ON t2_2_1.groupid = t2_2_2.groupid
							  ) AS t2_2
							ON t2_1.userid = t2_2.userid

							GROUP BY 1, 2, 3, 4
						  ) AS t2_0
						  WHERE start_dt >= "{2}"
						)

						SELECT simid ,1 AS stat_order ,userid ,uid FROM stats_tbl WHERE n_complete = 0
						UNION ALL
						SELECT simid ,2 AS stat_order ,userid ,uid FROM stats_tbl WHERE n_complete >= 1

					) AS t2
					ON t1.simid = t2.simid AND t1.stat_order = t2.stat_order;
					'''.format(
						', '.join([str(x) for x in sim_id]),
						cmp_user_groups,
						start_date,
						end_date,
						cmp_uid,
						', '.join([str(x) for x in list_simid]),
						def_simid,

						user_groups_merge,
					),
					db_connection
				)


			dict_df['dmg']['dmg_engagement'] = df_demog_engagement\
			.merge(
				df_demog,

				how='inner',
				on=['uid']
			)\
			.groupby(['simid', 'simname', 'stat_order', 'stat', 'bar_color'] + [x for x in df_demog.columns if x != 'uid' and '_ord' not in x])\
			.agg(_n = ('uid', 'nunique'))\
			.reset_index()\
			.sort_values(['simid', 'stat_order'])


			if dict_project is not None:
				dict_df['dmg']['dmg_engagement'] = dict_df['dmg']['dmg_engagement']\
				.assign(
					project = lambda x: x['simid'].apply(lambda y: dict_project_alt.get(y) if pd.notnull(y) else None)
				)



			del df_demog_engagement





		if skill_baseline:

			cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))
			cmp_show_hidden_skills = "" if show_hidden_skills else 'WHERE hidden = 0'

			demog_skill_baseline = pd.read_sql_query('''
				SELECT t1.simid ,t1.simname ,t1.orderid ,t1.skillname
					,t2.skillscore ,t2.userid ,t2.uid
					,"First Attempt" AS attempt
				FROM
				(
					SELECT t1_1.* ,t1_2.orderid ,t1_2.skillname ,t1_2.bench ,t1_2.hidden
					FROM
					(
						SELECT simid, TRIM(`name`) AS simname
						FROM simulation
						WHERE simid IN ({6})
					) AS t1_1

					INNER JOIN
					(
						SELECT simid ,orderid ,REPLACE(TRIM(`label`), '\u200b', '') AS skillname ,bench ,hidden
						FROM score
						{4}
					) AS t1_2
					ON t1_1.simid = t1_2.simid
				) AS t1

				LEFT JOIN
				(

					SELECT t2_1.simid ,t2_1.userid ,t2_2.uid ,t2_4.orderid ,t2_3.value AS skillscore
					FROM
					(
						SELECT *
						FROM
						(
							SELECT *
								,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
								,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS attempt
							FROM
							(
								SELECT DISTINCT {7} AS simid ,userid ,logid ,`start` ,`end` AS dt
								FROM user_sim_log
								WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{3}'
							) AS t2_1_1
						) AS t2_1_2
						WHERE attempt = 1 AND start_dt >= "{2}"
					) AS t2_1

					INNER JOIN
					(
						SELECT t2_3_1.userid ,t2_3_1.uid
						FROM
						(SELECT userid ,uid ,groupid FROM user where roleid = 1 {5}) AS t2_3_1
						{8} JOIN
						(SELECT groupid FROM user_group {1}) AS t2_3_2
						ON t2_3_1.groupid = t2_3_2.groupid
					) AS t2_2
					ON t2_1.userid = t2_2.userid

					LEFT JOIN
					(
						SELECT {7} AS simid ,userid ,logid ,scoreid ,value
						FROM sim_score_log
					) AS t2_3
					ON t2_1.simid = t2_3.simid AND t2_1.userid = t2_3.userid AND t2_1.logid = t2_3.logid

					LEFT JOIN
					(
						SELECT {7} AS simid ,scoreid ,orderid
						FROM score
					) AS t2_4
					ON t2_3.simid = t2_4.simid AND t2_3.scoreid = t2_4.scoreid

				) AS t2
				ON t1.simid = t2.simid AND t1.orderid = t2.orderid
				ORDER BY 1, 3;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					cmp_user_groups,
					start_date,
					end_date,
					cmp_show_hidden_skills,
					cmp_uid,

					', '.join([str(x) for x in list_simid]),
					def_simid,

					user_groups_merge
				),
				db_connection
			)


			dict_df['dmg']['dmg_skill_baseline'] = demog_skill_baseline\
			.merge(
				df_demog,

				how='inner',
				on=['uid']
			)\
			.groupby(['simid', 'simname', 'orderid', 'skillname' ,'attempt'] + [x for x in df_demog.columns if x != 'uid' and '_ord' not in x])\
			.agg(
				_n = ('skillscore', 'count'),
				_tot = ('skillscore', 'sum')
			)\
			.reset_index()\
			.sort_values(['simid', 'orderid'])


			if dict_project is not None:
				dict_df['dmg']['dmg_skill_baseline'] = dict_df['dmg']['dmg_skill_baseline']\
				.assign(
					project = lambda x: x['simid'].apply(lambda y: dict_project_alt.get(y) if pd.notnull(y) else None)
				)


			del demog_skill_baseline





		if decision_levels:

			cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))
			cmp_show_hidden_skills = "" if show_hidden_skills else 'WHERE hidden = 0'

			demog_decision_levels = pd.read_sql_query(
				'''
				SELECT *
				FROM
				(
					SELECT t2_1.simid ,t2_2.simname ,t2_1.attempt ,t2_4.decision_level_num ,t2_4.decision_ord ,t2_4.decisiontype ,t2_4.choice_num ,t2_1.userid ,t2_3.uid
						,ROW_NUMBER() OVER (PARTITION BY t2_1.simid ,t2_1.attempt ,t2_4.decision_level_num ,t2_1.userid ORDER BY t2_4.`end` DESC) AS dec_num
					FROM
					(
					  SELECT *
						  ,CASE
							  WHEN first_attempt = 1 THEN "First Attempt"
							  WHEN last_attempt = 1 THEN "Last Attempt"
						  END AS attempt
					  FROM
					  (
						  SELECT *
							  ,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
							  ,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt) AS first_attempt
							  ,ROW_NUMBER() OVER (PARTITION BY simid ,userid ORDER BY dt DESC) AS last_attempt
						  FROM
						  (
							  SELECT DISTINCT {6} AS simid ,userid ,logid ,`start` ,`end` AS dt
							  FROM user_sim_log
							  WHERE simid IN ({0}) AND complete = 1 AND DATE(`end`) <= '{4}'
						  ) AS t2_1_1
					  ) AS t2_1_2
					  WHERE (first_attempt = 1 OR (last_attempt = 1 AND first_attempt != 1)) AND start_dt >= "{3}"
					) AS t2_1

					INNER JOIN
					(
					  SELECT simid, TRIM(`name`) AS simname
					  FROM simulation
					  WHERE simid IN ({0})
					) AS t2_2
					ON t2_1.simid = t2_2.simid

					INNER JOIN
					(
					  SELECT t2_3_1.userid ,t2_3_1.uid
					  FROM
					  (SELECT userid ,uid ,groupid FROM user WHERE roleid = 1 {5}) AS t2_3_1
					  {1} JOIN
					  (SELECT groupid FROM user_group {2}) AS t2_3_2
					  ON t2_3_1.groupid = t2_3_2.groupid
					) AS t2_3
					ON t2_1.userid = t2_3.userid

					LEFT JOIN
					(
					  SELECT {6} AS simid ,userid ,logid ,relationid ,`end`
							,CASE
								WHEN relationtype = 1 THEN 3
								WHEN relationtype = 2 THEN 2
								WHEN relationtype = 3 THEN 1
							END AS decision_ord
							,CASE
								WHEN relationtype = 1 THEN "Critical"
								WHEN relationtype = 2 THEN "Suboptimal"
								WHEN relationtype = 3 THEN "Optimal"
							END AS decisiontype
							,{7}
							,{8}
					  FROM user_dialogue_log
					  WHERE simid IN ({0}) AND relationType <= 3 AND relationid IS NOT NULL
					) AS t2_4
					ON t2_1.simid = t2_4.simid AND t2_1.userid = t2_4.userid AND t2_1.logid = t2_4.logid
				) AS t0
				WHERE dec_num = 1;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					user_groups_merge,
					cmp_user_groups,

					start_date,
					end_date,
					cmp_uid,
					def_simid,
					def_decision_level,
					def_choice
				),
				db_connection
			)


			dict_df['dmg']['dmg_decision_levels'] = demog_decision_levels\
			.merge(
				df_demog,

				how='inner',
				on=['uid']
			)\
			.groupby(['simid', 'simname', 'attempt', 'decision_level_num' ,'decision_ord', 'decisiontype', 'choice_num'] + [x for x in df_demog.columns if x != 'uid' and '_ord' not in x])\
			.agg(
				_n = ('userid', 'count')
			)\
			.reset_index()\
			.sort_values(['simid', 'attempt', 'decision_level_num', 'decision_ord', 'choice_num'])




			if dict_df['dmg']['dmg_decision_levels'].shape[0] > 0:

				# Bring in Sim Section, Scenario and Decision Level text
				dict_df['dmg']['dmg_decision_levels'] = dict_df['dmg']['dmg_decision_levels']\
				.merge(
					# Sim Levels
					df_sim_levels\
					.query('performancebranch != 1')\
					.filter(['simid', 'sectionid', 'section', 'decision_level', 'decision_level_num', 'scenario'])\
					.drop_duplicates(),

					how='inner',
					on=['simid', 'decision_level_num']
				)

				# Bring in Choice text
				dict_df['dmg']['dmg_decision_levels'] = dict_df['dmg']['dmg_decision_levels']\
				.merge(
					df_sim_model_levels\
					.filter(['simid', 'sectionid', 'section', 'decision_level', 'decisiontype', 'choice_num', 'choice'])\
					.drop_duplicates(),

					how='left',
					on=['simid', 'sectionid', 'section', 'decision_level', 'decisiontype', 'choice_num']
				)



				# Fill in zeros
				dict_df['dmg']['dmg_decision_levels'] = dict_df['dmg']['dmg_decision_levels']\
				.merge(
					dict_df['dmg']['dmg_decision_levels']\
					.filter([x for x in df_demog.columns if x != 'uid' and '_ord' not in x] + ['simid', 'simname', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decision_ord', 'decisiontype', 'choice_num', 'choice'])\
					.drop_duplicates()\
					.merge(
						df_sql\
						.filter(['simid', 'attempt'])\
						.drop_duplicates(),

						how='left',
						on=['simid']
					),

					how='right',
					on=[x for x in df_demog.columns if x != 'uid' and '_ord' not in x] + ['simid', 'simname', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario', 'decision_ord', 'decisiontype', 'choice_num', 'choice', 'attempt']
				)\
				.assign(
					_n = lambda x: x['_n'].apply(lambda y: int(0) if pd.isnull(y) else int(y)),
					_denom = lambda x: x.groupby([x for x in df_demog.columns if x != 'uid' and '_ord' not in x] + ['simid', 'simname', 'attempt', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario'])['_n'].transform('sum'),
					#_total = lambda x: x.groupby([x for x in df_demog.columns if x != 'uid' and '_ord' not in x] + ['simid', 'simname', 'attempt', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario'])['n'].transform('sum'),
					#_pct = lambda x: x.apply(lambda y: 0 if pd.isnull(y['_total']) or y['_total'] == 0 else (y['_n']/y['_total'])*100, axis=1),

					bar_color = lambda x: x['decisiontype'].apply(lambda y: '#339933' if y =='Optimal' else '#ffb833' if y == 'Suboptimal' else '#e32726'),

					sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y)),
					decision_level_basic = lambda x: x['decision_level_num'].apply(lambda y: 'Decision Level ' + str(int(y)) if pd.notnull(y) else None)
				)\
				.assign(
					_meh = lambda x: x.groupby([x for x in df_demog.columns if x != 'uid' and '_ord' not in x] + ['simid', 'simname', 'attempt', 'sectionid', 'section', 'decision_level_num', 'decision_level', 'scenario'])['_n'].cumcount()+1,
					_denom = lambda x: x.apply(lambda y: y['_denom'] if y['_meh'] == 1 else 0, axis=1)
				)\
				.sort_values(['sim_order', 'attempt', 'sectionid', 'decision_level_num', 'decision_level', 'decision_ord', 'decisiontype', 'choice_num', 'choice'])\
				.drop(columns=['_meh'])




				# --- Get Coaching and Feedback --->
				dict_df['dmg']['dmg_decision_levels'] = dict_df['dmg']['dmg_decision_levels']\
				.merge(
					df_sim_model_levels\
					.filter(['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num', 'feedback', 'coaching'])\
					.groupby(['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num'])\
					.first()\
					.reset_index(),

					how='left',
					on=['simid', 'sectionid', 'decision_level_num', 'decision_level', 'decisiontype', 'choice_num']
				)\
				.assign(
					feedback = lambda x: x['feedback'].apply(lambda y: "-" if pd.isnull(y) else y),
					coaching = lambda x: x['coaching'].apply(lambda y: "-" if pd.isnull(y) else y),
				)



			if dict_project is not None:
				dict_df['dmg']['dmg_decision_levels'] = dict_df['dmg']['dmg_decision_levels']\
				.assign(
					project = lambda x: x['simid'].apply(lambda y: dict_project_alt.get(y) if pd.notnull(y) else None)
				)


			del demog_decision_levels
			if learner_engagement_last_7_days:
				cmp_user_groups = "" if user_groups == None else 'WHERE groupid IN ({0})'.format(', '.join([str(x) for x in user_groups]))


				# Convert many-to-one dictionary to a more correct version
				dict_project_alt = {}
				for k, v in dict_project.items():
					if isinstance(k, int):
						dict_project_alt[k] = v
					else:
						for key in list(k):
							dict_project_alt[key] = v
			
			
				project_var = '''
				CASE
				'''
			
			
				for key, value in dict_project.items():
					if isinstance(key, int):
						project_var += '''
						WHEN simid IN ({0}) THEN "{1}"
						'''.format(str(key), dict_project[key])
			
					else:
						project_var += '''
						WHEN simid IN ({0}) THEN "{1}"
						'''.format(",".join([str(x) for x in key]), dict_project[key])
			
				project_var += '''
				END AS project
				'''
			
			
				sql_query = '''
					SELECT simid ,simname
						,CAST(total AS UNSIGNED) AS total
						,stat_order ,stat
						,bar_color
						,n
						,CASE WHEN total > 0 THEN (n/total)*100 ELSE 0 END AS pct
					FROM
					(
						SELECT t1.*
							,SUM(CASE WHEN t1.stat_order in (1, 2) AND t2.n IS NOT NULL THEN t2.n ELSE 0 END) OVER (PARTITION BY t1.simid) AS total
							,CASE WHEN t2.n IS NULL THEN 0 ELSE t2.n END AS n
						FROM
						(
							SELECT *
							FROM
							(
								SELECT 3 AS stat_order ,"Completed (Last 7 days)" AS stat ,'#0b51c1' AS bar_color
							) AS t1_1,
							(
								SELECT simid, TRIM(`name`) AS simname
								FROM simulation
								WHERE simid IN ({0})
							) AS t1_2
						) AS t1
			
						LEFT JOIN
						(
							WITH
							stats_tbl AS
							(
								SELECT *
								FROM
								(
									SELECT t2_1.simid ,t2_1.userid ,t2_1.start_dt
										,SUM(t2_1.complete) AS n_complete
										,MAX(t2_1.dt) AS dt
									FROM
									(
										SELECT simid ,userid ,complete
											,CASE WHEN complete = 1 THEN `end` ELSE `start` END AS dt
											,MIN(DATE(`start`)) OVER (PARTITION BY simid ,userid) AS start_dt
										FROM user_sim_log
										WHERE simid IN ({0}) AND CASE WHEN complete = 0 THEN DATE(`start`) ELSE DATE(`end`) END <= '{3}'
									) AS t2_1
			
									INNER JOIN
									(
										SELECT t2_2_1.userid
										FROM
										(SELECT userid ,groupid FROM user WHERE roleid = 1) AS t2_2_1
										INNER JOIN
										(SELECT groupid FROM user_group {1}) AS t2_2_2
										ON t2_2_1.groupid = t2_2_2.groupid
									) AS t2_2
									ON t2_1.userid = t2_2.userid
			
									GROUP BY 1, 2, 3
								) AS t2_0
								WHERE start_dt >= "{2}"
							)
			
							SELECT simid ,3 AS stat_order ,COUNT(*) AS `n` FROM stats_tbl WHERE n_complete >= 1 GROUP BY 1, 2
			
						) AS t2
						ON t1.simid = t2.simid AND t1.stat_order = t2.stat_order
					) AS t0
					ORDER BY 1, 4;
				'''.format(
					', '.join([str(x) for x in sim_id]),
					cmp_user_groups,
					(pd.to_datetime(end_date) - timedelta(days=6)).strftime("%Y-%m-%d"),
					end_date,
				)
				dict_df['proj']['proj_engagement'] = pd.concat([
					dict_df['proj']['proj_engagement']\
					.assign(
						stat = "Completed (All Time)"),
					pd.read_sql_query(
						sql_query,
						db_connection
					)\
					.assign(
						project = lambda x: x['simid'].apply(lambda y: dict_project_alt.get(y) if pd.notnull(y) else None),
						sim_order = lambda x: x['simid'].apply(lambda y: dict_sim_order.get(y))
					)\
					.sort_values(['project', 'sim_order'])
				], ignore_index=True)\
				.assign(
					total = lambda x: x.groupby(['project'])['total'].transform('max'),
					pct = lambda x: (x['n']/x['total'])*100,
				)



	db_connection.close()
	tunnel.close()
	print('SSH Tunnel closed')

	del db_connection, tunnel

	return dict_df


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
					<script type = "text/javascript" src="chart_bar_horizontal.js"></script>
					<script type = "text/javascript" src="chart_bar_vertical_character.js"></script>
					<script type = "text/javascript" src="chart_donut.js"></script>
					<script type = "text/javascript" src="chart_line.js"></script>
					<script type = "text/javascript" src="chart_polar_mckinsey.js"></script>
					<script type = "text/javascript" src="createFilterData.js"></script>
					<script type = "text/javascript" src="chart_drag_drop.js"></script>
					<script type = "text/javascript" src="createSummaryData.js"></script>
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

				if({1}.value != ""){{

			'''.format(key1, selector)


			proj_selector = 'd["project"] == projSelector.value && ' if dict_project is not None else ''

			dmg_selector = 'd["demog_var"] == demogvarSelector.value && d["demog_val"] == demogvalSelector.value && ' if demog_filters is not None else ''



			for key2 in dict_df[key1]:
				if key2 == 'learner_engagement':
					html_page += '''
					// LEARNER ENGAGEMENT

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
							  .text(" learners have engaged with the Simulation.");

					}}
					else{{

						// --- First Text Grid Element --->
						d3.select("#text_component_{0}_1")
							  .append("p")
							  .attr("class", "component_text");


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
								.text(sing_plur_{0} + "engaged with the Simulation.");


						d3.select("#text_component_{0}_1").select(".component_text").append("br");
						d3.select("#text_component_{0}_1").select(".component_text").append("br");

						var em_val = 1;



						if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 1).map(d => d["n"])[0] > 0){{

						  d3.select("#text_component_{0}_1").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", em_val + "em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text(numFormat(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 1).map(d => d["pct"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 1).map(d => d["n"])[0]) + ")")
								.append("tspan")
								  .style("font-weight", 400)
								  .text(" of learners have not yet completed their first attempt.").append("br");

						  em_val += 1;

						}}

						d3.select("#text_component_{0}_1").select(".component_text")
							.append("text")
							.attr("dx", "0em")
							.attr("dy", em_val + "em")
							  .append("tspan")
								.style("font-weight", 700)
								.text(numFormat(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 2).map(d => d["pct"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 2).map(d => d["n"])[0]) + ")")
							  .append("tspan")
								.style("font-weight", 400)
								.text(" of learners have completed an attempt.").append("br");



						// --- First Chart Grid Element --->
						chart_donut(
						  data=data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] <= 2),
						  html_id="#chart_component_{0}_1",

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}},

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:"stat", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"alphabetical", ascending:true, show:false}},
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
							text:[
							  {{size:14, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:null}}]}},
							  {{size:14, weight:400, text:[
								{{var:"pct", format:",.1f", prefix:null, suffix:"%"}},
								{{var:"n", format:",.0f", prefix:" (", suffix:")"}},
							  ]}}
							]
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"stat", format:null, prefix:null, suffix:null}}]}},
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
							  {{var:"total", aggregate:"max", format:",.0f", prefix:null, suffix:null}},
							]}},
							{{size:18, weight:700, text:[{{var:null, aggregate:null, format:null, prefix:"Learners", suffix:null}}]}},
						  ],

						  yaxis={{
							height:400,
							offset:{{top:10, bottom:10}},
							tick:{{width:100}}
						  }},

						  font={{family:body_font}},

						  margin={{top:10, bottom:10, left:10, right:10, g:10}},

						  canvas={{width:500}},

						  zoom=false
						);



						if(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 3).map(d => d["n"])[0] == 0){{

						  // --- Second Text Grid Element --->
						  d3.select("#text_component_{0}_2")
								.append("p")
								.attr("class", "component_text");

						  d3.select("#text_component_{0}_2").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "1em")
								.append("tspan")
								  .style("font-weight", 700)
								  .text("0")
								.append("tspan")
								  .style("font-weight", 400)
								  .text(" learners have completed multiple attempts.").append("br");

						}}
						else{{

						  // --- Second Text Grid Element --->
						  d3.select("#text_component_{0}_2")
								.append("p")
								.attr("class", "component_text");

						  d3.select("#text_component_{0}_2").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "1em")
							  .append("tspan")
								  .style("font-weight", 700)
								  .text(numFormat(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 3).map(d => d["pct"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 3).map(d => d["n"])[0]) + ")")
							  .append("tspan")
								  .style("font-weight", 400)
								  .text(" of learners have completed")
							  .append("tspan")
								  .style("font-weight", 700)
								  .text(" 2 or more")
							  .append("tspan")
								  .style("font-weight", 400)
								  .text(" attempts.").append("br");


						  d3.select("#text_component_{0}_2").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "2em")
							  .append("tspan")
								  .style("font-weight", 700)
								  .text(numFormat(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 4).map(d => d["pct"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 4).map(d => d["n"])[0]) + ")")
							  .append("tspan")
								  .style("font-weight", 400)
								  .text(" of learners have completed")
							  .append("tspan")
								  .style("font-weight", 700)
								  .text(" 3 or more")
							  .append("tspan")
								  .style("font-weight", 400)
								  .text(" attempts.").append("br");


						  d3.select("#text_component_{0}_2").select(".component_text")
							  .append("text")
							  .attr("dx", "0em")
							  .attr("dy", "3em")
							   .append("tspan")
								   .style("font-weight", 700)
								   .text(numFormat(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 5).map(d => d["pct"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} {2} d["simname"] == simSelector.value && d["stat_order"] == 5).map(d => d["n"])[0]) + ")")
							   .append("tspan")
								   .style("font-weight", 400)
								   .text(" of learners have completed")
							   .append("tspan")
								   .style("font-weight", 700)
								   .text(" 4 or more")
							   .append("tspan")
								   .style("font-weight", 400)
								   .text(" attempts.").append("br");



							// --- Second Chart Grid Element --->
							d3.select("#chart_component_{0}_2").selectAll('.svg-container').remove();
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

					// --- First Text Grid Element --->
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
					html_page += '''
					// PROJECT - LEARNER ENGAGEMENT

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

					d3.select("#text_component_{0}_1").select(".component_text")
					  .append("text")
					  .attr("dx", "0em")
					  .attr("dy", "0em")
						.append("tspan")
						  .style("font-weight", 700)
						  .text(d3.format(",.0f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total"])[0]))
						.append("tspan")
						  .style("font-weight", 400)
						  .text(" learners have completed an attempt of ")
						.append("tspan")
						  .style("font-weight", 700)
						  .text("at least one ")
						.append("tspan")
						  .style("font-weight", 400)
						  .text("Simulation.");

					d3.select("#text_component_{0}_1").select(".component_text").append("br");

					d3.select("#text_component_{0}_1").select(".component_text")
						.append("text")
						.attr("dx", "0em")
						.attr("dy", "0em")
							.append("tspan")
								.style("font-weight", 700)
								.text(d3.format(",.1f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["pct_all_complete"])[0]) + "% (" + d3.format(",.0f")(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total_all_complete"])[0]) + ")")
							.append("tspan")
								.style("font-weight", 400)
								.text(" of learners have completed ")
							.append("tspan")
								.style("font-weight", 700)
								.text("all ")
							.append("tspan")
								.style("font-weight", 400)
								.text("Sims.");



					if(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["total"])[0] > 0){{

						d3.select("#chart_component_{0}_1").selectAll('.svg-container').remove();
						chart_bar_horizontal(
						  data=data_component_{0}.filter(d => {1} d["project"] == projSelector.value),
						  html_id="#chart_component_{0}_1",

						  x={{var:"n", ascending:true, ci:[null, null]}}, // Must be numeric
						  y={{var:"simname", order:"as_appear", ascending:true}}, // Must be categorical

						  title={{value:null, line:false}},

						  clr={{var:"bar_color", value:null}}, // Variable containing color of bar(s) or value to set all bars to same color
						  opacity={{var:null, value:1.0}}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

						  facet={{var:null, size:18, weight:400, space_above_title:5, order:"as_appear", ascending:true, line:{{show:false, color:"#d3d2d2"}}}},
						  group={{var:"stat", label:{{value:null, size:18, weight:700}}, size:14, weight:400, order:"as_appear", ascending:true, show:true}},
						  switcher={{var:null, label:{{value:null, size:18, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},
						  scroll={{var:null, label:{{value:null, size:20, weight:700}}, size:18, weight:400, order:"as_appear", ascending:true, line:false}},

						  bar={{
							size:12, weight:400,
							text:[
								{{var:"n", format:",.0f", prefix:null, suffix:null}},
								{{var:"pct", format:",.1f", prefix:"(", suffix:"%)"}},
							],
							extra_height:0,
							space_between:10
						  }},

						  tooltip_text=[
							{{size:16, weight:700, text:[{{var:"simname", format:null, prefix:null, suffix:null}}]}},
							{{size:8, weight:700, text:[{{var:null, format:null, prefix:null, suffix:null}}]}},
							{{size:14, weight:700, text:[{{var:"n", format:",.0f", prefix:null, suffix:" Learners"}}]}},
							{{size:14, weight:400, text:[{{var:"pct", format:",.1f", prefix:"(", suffix:"%)"}}]}}
						  ],

						  barmode="group", // "group", "stack" or "overlay"

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
							num_ticks:Math.min(7, (d3.max(data_component_{0}.filter(d => {1} d["project"] == projSelector.value).map(d => d["n"])))+1),
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