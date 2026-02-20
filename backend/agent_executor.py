"""
Agent script executor with GCS support
"""
import asyncio
import subprocess
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from google.cloud import storage

logger = logging.getLogger(__name__)


async def run_agent_script(
    job_id: str,
    agent_id: str,
    user_email: str,
    db,
    agent: dict,
    ROOT_DIR: Path,
    OUTPUTS_DIR: Path,
    RESEND_API_KEY: str,
    SENDER_EMAIL: str,
    resend_module
):
    """Background task to run agent script with validation and main processing - Local storage only"""
    try:
        logger.info(f"Starting job {job_id} for agent {agent_id}")
        
        # Update job status to processing
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Get job info
        job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        
        # Get input files metadata
        input_files = await db.files.find({"job_id": job_id}, {"_id": 0}).to_list(100)
        
        # Prepare file info for scripts
        file_info = {
            "job_id": job_id,
            "agent_id": agent_id,
            "files": []
        }
        
        for file_doc in input_files:
            file_entry = {
                "filename": file_doc["file_name"],
                "storage_type": "local",
                "local_path": file_doc["file_path"]
            }
            file_info["files"].append(file_entry)
        
        # Save file info as JSON for scripts to read
        job_config_path = ROOT_DIR / "temp" / f"{job_id}_config.json"
        job_config_path.parent.mkdir(exist_ok=True)
        with open(job_config_path, 'w') as f:
            json.dump(file_info, f, indent=2)
        
        # Run validation script if provided
        validation_script = agent.get('validation_script')
        validation_output = ""
        
        if validation_script and os.path.exists(validation_script):
            logger.info(f"Running validation script for job {job_id}")
            
            # Use the same Python interpreter that's running this code
            python_executable = sys.executable
            
            result = subprocess.run(
                [python_executable, validation_script, str(job_config_path)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Capture output
            validation_output = f"=== VALIDATION OUTPUT ===\n{result.stdout}\n"
            if result.stderr:
                validation_output += f"\n=== STDERR ===\n{result.stderr}\n"
            
            # Store validation output
            await db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"validation_output": validation_output}}
            )
            
            if result.returncode != 0:
                error_msg = f"Validation failed:\n{validation_output}"
                logger.error(error_msg)
                await db.jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "status": "failed",
                        "error_message": error_msg,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                return
            
            logger.info(f"Validation passed for job {job_id}")
        
        # Run main script if provided
        main_script = agent.get('main_script')
        execution_output = ""
        
        if main_script and os.path.exists(main_script):
            logger.info(f"Running main script for job {job_id}")
            
            # Prepare output directory/path
            if gcs_client and (agent.get('gcs_bucket') or GCS_DEFAULT_BUCKET):
                bucket_name = agent.get('gcs_bucket') or GCS_DEFAULT_BUCKET
                output_path = f"gs://{bucket_name}/jobs/{job_id}/output"
            else:
                job_output_dir = OUTPUTS_DIR / job_id
                job_output_dir.mkdir(exist_ok=True)
                output_path = str(job_output_dir)
            
            # Add output path to config
            file_info["output_path"] = output_path
            with open(job_config_path, 'w') as f:
                json.dump(file_info, f, indent=2)
            
            result = subprocess.run(
                [python_executable, main_script, str(job_config_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            # Capture output
            execution_output = f"=== EXECUTION OUTPUT ===\n{result.stdout}\n"
            if result.stderr:
                execution_output += f"\n=== STDERR ===\n{result.stderr}\n"
            
            # Store execution output
            await db.jobs.update_one(
                {"job_id": job_id},
                {"$set": {"execution_output": execution_output}}
            )
            
            if result.returncode != 0:
                error_msg = f"Processing failed:\n{execution_output}"
                logger.error(error_msg)
                await db.jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "status": "failed",
                        "error_message": error_msg,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                return
            
            logger.info(f"Main script completed for job {job_id}")
            
            # List output files
            output_files = []
            if gcs_client and (agent.get('gcs_bucket') or GCS_DEFAULT_BUCKET):
                bucket_name = agent.get('gcs_bucket') or GCS_DEFAULT_BUCKET
                bucket = gcs_client.bucket(bucket_name)
                blobs = bucket.list_blobs(prefix=f"jobs/{job_id}/output/")
                output_files = [blob.name.split('/')[-1] for blob in blobs if not blob.name.endswith('/')]
            else:
                job_output_dir = OUTPUTS_DIR / job_id
                if job_output_dir.exists():
                    output_files = [f.name for f in job_output_dir.iterdir() if f.is_file()]
        
        else:
            # No scripts provided - use mock processing
            logger.info(f"No scripts provided, using mock processing for job {job_id}")
            await asyncio.sleep(3)
            
            # Generate mock output
            job_output_dir = OUTPUTS_DIR / job_id
            job_output_dir.mkdir(exist_ok=True)
            
            output_file_name = f"output_{job_id}.txt"
            output_file_path = job_output_dir / output_file_name
            
            with open(output_file_path, 'w') as f:
                f.write(f"Job ID: {job_id}\n")
                f.write(f"Agent: {agent['name']}\n")
                f.write(f"Processed at: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Input files: {', '.join([f['filename'] for f in file_info['files']])}\n")
                f.write("\nProcessing completed successfully!\n")
            
            output_files = [output_file_name]
        
        # Update job with output
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "completed",
                "output_files": output_files,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Send email notification
        if RESEND_API_KEY:
            try:
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2563EB;">Job Completed Successfully</h2>
                        <p>Your automation job has been processed successfully.</p>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Job ID:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{job_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Agent:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{agent['name']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Status:</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #ddd;">Completed</td>
                            </tr>
                        </table>
                        <p>Your output files are ready for download on the platform.</p>
                        <p style="margin-top: 30px; color: #666; font-size: 12px;">This is an automated message from FlowHub.</p>
                    </div>
                </body>
                </html>
                """
                
                params = {
                    "from": SENDER_EMAIL,
                    "to": [user_email],
                    "subject": f"Job Completed: {agent['name']}",
                    "html": html_content
                }
                
                await asyncio.to_thread(resend_module.Emails.send, params)
                logger.info(f"Email sent to {user_email} for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
        
        # Clean up temp config
        if job_config_path.exists():
            job_config_path.unlink()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except subprocess.TimeoutExpired:
        error_msg = "Script execution timed out"
        logger.error(f"Job {job_id} timed out")
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error_message": error_msg,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
