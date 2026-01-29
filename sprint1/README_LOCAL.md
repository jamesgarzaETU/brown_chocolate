
# Sprint 1 - Dashboard Local Development

This folder contains the setup for working on the Skillwell Dashboard visualization locally.

## Prerequisities

- Python 3.8+
- Pandas
- Plotly

## Quick Start (Local)

You can generate the dashboard locally using the provided mock data (`skillwell_etl/data.pkl`).

1.  **Navigate to this folder**:
    ```bash
    cd sprint1
    ```

2.  **Run the Reporting Script**:
    ```bash
    python3 skillwell_etl/reporting.py --local
    ```
    
    This will:
    - Load data from `skillwell_etl/data.pkl` (Mock data is provided by default).
    - Generate `skillwell_etl/dashboard.html`.

3.  **View Dashboard**:
    Open `skillwell_etl/dashboard.html` in your browser.

## Generating Real Data (If authorized)

If you have AWS credentials and access to the S3 bucket:

1.  Ensure you have `boto3` installed and credentials configured.
2.  Run the POC data processing script:
    ```bash
    python3 1_process_data_poc.py
    ```
    This will generate a *real* `data.pkl` file (overwriting the mock one) which you can then use with the reporting script.

## Project Structure

- `1_process_data_poc.py`: The main ETL script (generates `data.pkl`).
- `skillwell_etl/`: Package containing the reporting logic.
    - `reporting.py`: Main script for generating the dashboard.
    - `pipeline.py`: S3/Parquet handling (mostly ignored in local mode).
    - `transform.py`: Data transformation logic.
- `code_simulation_3_demographic_data.xlsx`: Required reference data.
