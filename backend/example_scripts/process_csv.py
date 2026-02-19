#!/usr/bin/env python3
"""
Example main processing script for CSV files

Usage: python process_csv.py <config_json_path>

The config JSON contains:
{
  "job_id": "job_abc123",
  "agent_id": "agent_xyz",
  "output_path": "gs://my-bucket/jobs/job_abc123/output" or "/local/path",
  "files": [...]
}
"""

import sys
import json
import pandas as pd
from google.cloud import storage
import io
from pathlib import Path

def process_csv(config_path):
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Processing files for job: {config['job_id']}")
    
    all_data = []
    
    # Read and process all CSV files
    for file_info in config['files']:
        filename = file_info['filename']
        
        if not filename.lower().endswith('.csv'):
            continue
        
        print(f"Processing: {filename}")
        
        # Read CSV
        if file_info['storage_type'] == 'gcs':
            storage_client = storage.Client()
            bucket = storage_client.bucket(file_info['gcs_bucket'])
            blob = bucket.blob(file_info['gcs_blob_name'])
            csv_content = blob.download_as_text()
            df = pd.read_csv(io.StringIO(csv_content))
        else:
            df = pd.read_csv(file_info['local_path'])
        
        # Example processing: calculate total revenue
        if 'Revenue' in df.columns:
            total_revenue = df['Revenue'].sum()
            print(f"  Total Revenue: ${total_revenue:,.2f}")
        
        all_data.append(df)
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined data: {len(combined_df)} total rows")
    
    # Generate output
    output_filename = f"processed_{config['job_id']}.csv"
    output_path = config['output_path']
    
    if output_path.startswith('gs://'):
        # Upload to GCS
        parts = output_path.replace('gs://', '').split('/', 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ''
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"{prefix}/{output_filename}" if prefix else output_filename
        blob = bucket.blob(blob_name)
        
        # Upload DataFrame as CSV
        csv_buffer = io.StringIO()
        combined_df.to_csv(csv_buffer, index=False)
        blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')
        
        print(f"\n✓ Output uploaded to: gs://{bucket_name}/{blob_name}")
    else:
        # Save locally
        output_file = Path(output_path) / output_filename
        combined_df.to_csv(output_file, index=False)
        print(f"\n✓ Output saved to: {output_file}")
    
    print("Processing completed successfully!")
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python process_csv.py <config_json_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    sys.exit(process_csv(config_path))
