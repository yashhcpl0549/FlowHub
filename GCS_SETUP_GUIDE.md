# Google Cloud Storage Setup Guide for FlowHub

FlowHub supports storing agent input/output files in Google Cloud Storage, allowing your validation and processing scripts to read from and write to GCS buckets.

## Quick Start

### 1. Create GCS Bucket

```bash
# Using gcloud CLI
gcloud storage buckets create gs://your-flowhub-bucket --location=us-central1

# Or create via Google Cloud Console:
# https://console.cloud.google.com/storage
```

### 2. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create flowhub-service \
    --display-name="FlowHub Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:flowhub-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create and download key
gcloud iam service-accounts keys create /path/to/flowhub-key.json \
    --iam-account=flowhub-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Configure FlowHub

Update `/app/backend/.env`:

```bash
GCS_DEFAULT_BUCKET="your-flowhub-bucket"
GOOGLE_APPLICATION_CREDENTIALS="/app/backend/flowhub-key.json"
```

Copy the service account JSON to the server:
```bash
cp /path/to/flowhub-key.json /app/backend/flowhub-key.json
```

Restart backend:
```bash
sudo supervisorctl restart backend
```

## Usage

### Default Bucket (Shared)

All agents use the default bucket unless specified otherwise. Files are organized by job:

```
your-flowhub-bucket/
  jobs/
    job_abc123/
      0_sales_data.csv
      1_customer_list.xlsx
      output/
        processed_abc123.csv
```

### Custom Bucket Per Agent

When creating an agent via admin panel:
1. Fill in agent details
2. In "Google Cloud Storage Bucket" field, enter custom bucket name
3. That agent will use its dedicated bucket

Example bucket structure:
```
sales-agent-bucket/          # Custom bucket for sales agent
  jobs/
    job_xyz/...

inventory-agent-bucket/      # Custom bucket for inventory agent
  jobs/
    job_123/...
```

## File Naming Convention

FlowHub automatically names uploaded files:
- Pattern: `jobs/{job_id}/{index}_{original_filename}`
- Example: `jobs/job_a1b2c3/0_sales_report.csv`

Output files:
- Pattern: `jobs/{job_id}/output/{your_filename}`
- Example: `jobs/job_a1b2c3/output/processed_report.csv`

## Writing Agent Scripts

### Config JSON Structure

Your scripts receive a JSON config file with all file information:

```json
{
  "job_id": "job_abc123",
  "agent_id": "agent_xyz",
  "output_path": "gs://your-bucket/jobs/job_abc123/output",
  "files": [
    {
      "filename": "sales_data.csv",
      "storage_type": "gcs",
      "gcs_bucket": "your-bucket",
      "gcs_blob_name": "jobs/job_abc123/0_sales_data.csv",
      "gcs_path": "gs://your-bucket/jobs/job_abc123/0_sales_data.csv"
    }
  ]
}
```

### Reading Files from GCS

#### CSV Files
```python
from google.cloud import storage
import pandas as pd
import io

def read_csv_from_gcs(file_info):
    client = storage.Client()
    bucket = client.bucket(file_info['gcs_bucket'])
    blob = bucket.blob(file_info['gcs_blob_name'])
    
    csv_content = blob.download_as_text()
    df = pd.read_csv(io.StringIO(csv_content))
    return df
```

#### Excel Files
```python
def read_excel_from_gcs(file_info):
    client = storage.Client()
    bucket = client.bucket(file_info['gcs_bucket'])
    blob = bucket.blob(file_info['gcs_blob_name'])
    
    bytes_content = blob.download_as_bytes()
    df = pd.read_excel(io.BytesIO(bytes_content))
    return df
```

#### JSON Files
```python
import json

def read_json_from_gcs(file_info):
    client = storage.Client()
    bucket = client.bucket(file_info['gcs_bucket'])
    blob = bucket.blob(file_info['gcs_blob_name'])
    
    json_content = blob.download_as_text()
    data = json.loads(json_content)
    return data
```

### Writing Output to GCS

```python
from google.cloud import storage
import pandas as pd
import io

def write_csv_to_gcs(df, output_path, filename):
    # Parse GCS path: gs://bucket/path/to/folder
    parts = output_path.replace('gs://', '').split('/', 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    # Upload
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_name = f"{prefix}/{filename}"
    blob = bucket.blob(blob_name)
    
    # Convert DataFrame to CSV string and upload
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    blob.upload_from_string(
        csv_buffer.getvalue(),
        content_type='text/csv'
    )
    
    print(f"Uploaded to: gs://{bucket_name}/{blob_name}")
```

### Complete Example: Validation Script

```python
#!/usr/bin/env python3
import sys
import json
import pandas as pd
from google.cloud import storage
import io

def validate(config_path):
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Validating job: {config['job_id']}")
    
    # Expected columns
    REQUIRED_COLUMNS = ['Date', 'Product', 'Quantity', 'Revenue']
    
    for file_info in config['files']:
        if not file_info['filename'].endswith('.csv'):
            continue
        
        print(f"Checking {file_info['filename']}...")
        
        # Read from GCS
        if file_info['storage_type'] == 'gcs':
            client = storage.Client()
            bucket = client.bucket(file_info['gcs_bucket'])
            blob = bucket.blob(file_info['gcs_blob_name'])
            csv_content = blob.download_as_text()
            df = pd.read_csv(io.StringIO(csv_content))
        else:
            df = pd.read_csv(file_info['local_path'])
        
        # Validate columns
        missing = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            print(f"ERROR: Missing columns: {missing}")
            return 1
        
        print(f"✓ Valid ({len(df)} rows)")
    
    return 0

if __name__ == '__main__':
    sys.exit(validate(sys.argv[1]))
```

### Complete Example: Processing Script

```python
#!/usr/bin/env python3
import sys
import json
import pandas as pd
from google.cloud import storage
import io

def process(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Processing job: {config['job_id']}")
    
    # Read all CSV files
    dataframes = []
    for file_info in config['files']:
        if not file_info['filename'].endswith('.csv'):
            continue
        
        if file_info['storage_type'] == 'gcs':
            client = storage.Client()
            bucket = client.bucket(file_info['gcs_bucket'])
            blob = bucket.blob(file_info['gcs_blob_name'])
            csv_content = blob.download_as_text()
            df = pd.read_csv(io.StringIO(csv_content))
        else:
            df = pd.read_csv(file_info['local_path'])
        
        dataframes.append(df)
    
    # Combine and process
    combined = pd.concat(dataframes, ignore_index=True)
    
    # Your processing logic here
    result = combined.groupby('Product')['Revenue'].sum().reset_index()
    
    # Write output to GCS
    output_path = config['output_path']
    parts = output_path.replace('gs://', '').split('/', 1)
    bucket_name = parts[0]
    prefix = parts[1]
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"{prefix}/summary.csv")
    
    csv_buffer = io.StringIO()
    result.to_csv(csv_buffer, index=False)
    blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')
    
    print(f"✓ Output saved to {output_path}/summary.csv")
    return 0

if __name__ == '__main__':
    sys.exit(process(sys.argv[1]))
```

## Testing Locally

### 1. Set credentials
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/flowhub-key.json"
```

### 2. Create test config
```json
{
  "job_id": "test_job",
  "agent_id": "test_agent",
  "output_path": "gs://your-bucket/jobs/test_job/output",
  "files": [
    {
      "filename": "test.csv",
      "storage_type": "gcs",
      "gcs_bucket": "your-bucket",
      "gcs_blob_name": "test/test.csv",
      "gcs_path": "gs://your-bucket/test/test.csv"
    }
  ]
}
```

### 3. Run script
```bash
python your_script.py test_config.json
```

## Permissions

### Minimum Required Permissions

Service account needs:
- `storage.objects.create` - Upload files
- `storage.objects.get` - Read files
- `storage.objects.list` - List files in bucket
- `storage.objects.delete` - Delete files (optional)

Predefined role: `roles/storage.objectAdmin`

### Multiple Buckets

If using custom buckets per agent, grant permissions to all buckets:

```bash
# For each bucket
gsutil iam ch serviceAccount:flowhub-service@PROJECT.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://agent-specific-bucket
```

## Cost Optimization

### Storage Classes
- **Standard**: Frequently accessed data
- **Nearline**: < 1/month access (30-day minimum)
- **Coldline**: < 1/quarter access (90-day minimum)

```bash
# Set lifecycle policy
gsutil lifecycle set lifecycle.json gs://your-bucket
```

Example `lifecycle.json`:
```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      }
    ]
  }
}
```

### Monitoring Costs
```bash
# Check bucket size
gsutil du -sh gs://your-bucket

# List large files
gsutil ls -lh gs://your-bucket/** | sort -k1 -h -r | head -20
```

## Troubleshooting

### "Permission Denied" Errors

1. Check credentials file exists:
   ```bash
   ls -la /app/backend/flowhub-key.json
   ```

2. Verify service account has permissions:
   ```bash
   gsutil iam get gs://your-bucket
   ```

3. Test authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/app/backend/flowhub-key.json"
   gsutil ls gs://your-bucket
   ```

### "Bucket Not Found" Errors

1. Check bucket exists:
   ```bash
   gsutil ls
   ```

2. Verify bucket name in `.env` (no `gs://` prefix)

3. Check bucket is in correct project

### Script Execution Errors

Check backend logs:
```bash
tail -f /var/log/supervisor/backend.err.log
```

Look for:
- Import errors (missing `google-cloud-storage`)
- Authentication errors
- GCS API errors

## Security Best Practices

1. **Use least privilege** - Only grant necessary permissions
2. **Rotate keys regularly** - Create new service account keys periodically
3. **Use separate buckets** - Different environments (dev/prod)
4. **Enable versioning** - Recover from accidental deletions
5. **Set up logging** - Monitor bucket access
6. **Use VPC Service Controls** - Restrict bucket access

## Example Bucket Organization

```
your-flowhub-bucket/
├── jobs/
│   ├── job_abc123/
│   │   ├── 0_sales_data.csv
│   │   ├── 1_customers.xlsx
│   │   └── output/
│   │       └── report.csv
│   └── job_def456/
│       └── ...
├── scripts/           # Optional: Store reusable scripts
│   ├── validation/
│   └── processing/
└── templates/         # Optional: Template files
    └── report_template.xlsx
```

## Next Steps

1. ✅ Set up GCS bucket and service account
2. ✅ Configure FlowHub `.env` file
3. ✅ Test connection (check backend logs)
4. ✅ Create an agent with custom scripts
5. ✅ Upload test files and verify they appear in GCS
6. ✅ Execute agent and check output in GCS

## Support

For issues or questions:
- Check backend logs: `tail -f /var/log/supervisor/backend.*.log`
- Verify GCS setup: `gsutil ls gs://your-bucket/jobs/`
- Review example scripts in `/app/backend/example_scripts/`
