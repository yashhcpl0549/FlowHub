# FlowHub Agent Scripts

This directory contains example validation and processing scripts for FlowHub agents.

## How It Works

### 1. File Upload & Storage
When users upload files to an agent:
- Files are stored in Google Cloud Storage (if configured) or local storage
- Each file gets a standardized path: `gs://bucket/jobs/{job_id}/{index}_{filename}`
- File metadata is stored in MongoDB

### 2. Script Execution
When an agent is executed:
1. A JSON config file is generated with all file information
2. Validation script runs first (if provided)
3. Main processing script runs (if validation passed)
4. Output files are stored in the designated output path

### 3. Config JSON Format
```json
{
  "job_id": "job_abc123",
  "agent_id": "agent_xyz",
  "output_path": "gs://my-bucket/jobs/job_abc123/output",
  "files": [
    {
      "filename": "sales_data.csv",
      "storage_type": "gcs",
      "gcs_bucket": "my-bucket",
      "gcs_blob_name": "jobs/job_abc123/0_sales_data.csv",
      "gcs_path": "gs://my-bucket/jobs/job_abc123/0_sales_data.csv"
    }
  ]
}
```

## Example Scripts

### validate_csv.py
Validates that uploaded CSV files contain required columns.

**Customize**:
- Edit `EXPECTED_COLUMNS` list to match your requirements
- Add additional validation logic (data types, value ranges, etc.)

### process_csv.py
Reads CSV files, performs processing, and generates output.

**Customize**:
- Add your specific business logic
- Calculate metrics, transform data, generate reports
- Output can be CSV, Excel, JSON, or any format

## Creating Your Own Scripts

### Validation Script Template
```python
import sys
import json
from google.cloud import storage
import pandas as pd

def validate(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Your validation logic here
    # Return 0 for success, non-zero for failure
    
    return 0

if __name__ == '__main__':
    sys.exit(validate(sys.argv[1]))
```

### Main Script Template
```python
import sys
import json
from google.cloud import storage

def process(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Read input files
    # Process data
    # Save output to config['output_path']
    
    return 0

if __name__ == '__main__':
    sys.exit(process(sys.argv[1]))
```

## Reading Files from GCS

### CSV Files
```python
from google.cloud import storage
import pandas as pd
import io

storage_client = storage.Client()
bucket = storage_client.bucket(file_info['gcs_bucket'])
blob = bucket.blob(file_info['gcs_blob_name'])
csv_content = blob.download_as_text()
df = pd.read_csv(io.StringIO(csv_content))
```

### Excel Files
```python
blob = bucket.blob(file_info['gcs_blob_name'])
bytes_content = blob.download_as_bytes()
df = pd.read_excel(io.BytesIO(bytes_content))
```

### JSON Files
```python
blob = bucket.blob(file_info['gcs_blob_name'])
json_content = blob.download_as_text()
data = json.loads(json_content)
```

## Writing Output to GCS

```python
from google.cloud import storage
import io

# Parse GCS path
output_path = config['output_path']  # e.g., gs://bucket/jobs/123/output
parts = output_path.replace('gs://', '').split('/', 1)
bucket_name = parts[0]
prefix = parts[1]

# Upload file
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)
blob = bucket.blob(f"{prefix}/result.csv")
blob.upload_from_filename('local_file.csv')
# or
blob.upload_from_string(data_string, content_type='text/csv')
```

## Dependencies

Make sure your scripts can import required libraries:
```bash
pip install pandas google-cloud-storage openpyxl
```

## Testing Locally

1. Set GCS credentials:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   ```

2. Create a test config JSON:
   ```json
   {"job_id": "test", "files": [...]}
   ```

3. Run your script:
   ```bash
   python your_script.py test_config.json
   ```
