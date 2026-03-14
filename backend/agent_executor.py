"""
Agent script executor - Supports GCS storage
"""
import asyncio
import subprocess
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_agent_script(
    job_id: str,
    agent_id: str,
    user_email: str,
    db,
    agent: dict,
    ROOT_DIR: Path,
    OUTPUTS_DIR: Path,
    SMTP_EMAIL: str,
    SMTP_APP_PASSWORD: str,
    gcs_bucket=None
):
    """Background task to run agent script with validation and main processing"""
    try:
        logger.info(f"Starting job {job_id} for agent {agent_id}")

        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

        # Get input files metadata from DB
        input_files = await db.files.find({"job_id": job_id}, {"_id": 0}).to_list(100)

        # Build file info for scripts
        # Supports both gcs_path (new) and file_path (legacy local) storage
        file_info = {
            "job_id": job_id,
            "agent_id": agent_id,
            "files": []
        }

        for file_doc in input_files:
            file_entry = {
                "filename": file_doc["file_name"],
                "storage_type": file_doc.get("storage_type", "local"),
                "gcs_path": file_doc.get("gcs_path", ""),
                "local_path": file_doc.get("file_path", "")
            }
            file_info["files"].append(file_entry)

        # Save config JSON for scripts to read
        job_config_path = ROOT_DIR / "temp" / f"{job_id}_config.json"
        job_config_path.parent.mkdir(exist_ok=True)
        with open(job_config_path, 'w') as f:
            json.dump(file_info, f, indent=2)

        python_executable = sys.executable

        # ── Validation script ─────────────────────────────────────────────────
        validation_script = agent.get('validation_script')
        validation_output = ""

        if validation_script and os.path.exists(validation_script):
            logger.info(f"Running validation script for job {job_id}")

            result = subprocess.run(
                [python_executable, validation_script, str(job_config_path)],
                capture_output=True,
                text=True,
                timeout=120
            )

            validation_output = f"=== VALIDATION OUTPUT ===\n{result.stdout}\n"
            if result.stderr:
                validation_output += f"\n=== STDERR ===\n{result.stderr}\n"

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

        # ── Main script ───────────────────────────────────────────────────────
        main_script = agent.get('main_script')
        execution_output = ""

        if main_script and os.path.exists(main_script):
            logger.info(f"Running main script for job {job_id}")

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
                timeout=7200  # 2 hours
            )

            execution_output = f"=== EXECUTION OUTPUT ===\n{result.stdout}\n"
            if result.stderr:
                execution_output += f"\n=== STDERR ===\n{result.stderr}\n"

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

            output_files = []
            if job_output_dir.exists():
                output_files = [f.name for f in job_output_dir.iterdir() if f.is_file()]

                # Upload outputs to GCS if configured
                if gcs_bucket and output_files:
                    for output_file in output_files:
                        try:
                            local_path = job_output_dir / output_file
                            gcs_path = f"outputs/{job_id}/{output_file}"
                            blob = gcs_bucket.blob(gcs_path)
                            blob.upload_from_filename(str(local_path))
                            logger.info(f"Uploaded output {output_file} to GCS")
                        except Exception as e:
                            logger.error(f"Failed to upload {output_file} to GCS: {e}")

        else:
            # No scripts — mock output
            logger.info(f"No scripts provided, using mock processing for job {job_id}")
            await asyncio.sleep(3)

            job_output_dir = OUTPUTS_DIR / job_id
            job_output_dir.mkdir(exist_ok=True)
            output_file_name = f"output_{job_id}.txt"
            with open(job_output_dir / output_file_name, 'w') as f:
                f.write(f"Job ID: {job_id}\nAgent: {agent['name']}\n")
            output_files = [output_file_name]

        # ── Mark complete ─────────────────────────────────────────────────────
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "completed",
                "output_files": output_files,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        # ── Email notification ────────────────────────────────────────────────
        if SMTP_EMAIL and SMTP_APP_PASSWORD and user_email:
            try:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                html_content = f"""
                <html><body style="font-family: Arial, sans-serif; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2563EB;">Job Completed Successfully</h2>
                        <p>Your automation job has been processed successfully.</p>
                        <table style="width:100%; border-collapse:collapse; margin:20px 0;">
                            <tr><td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Job ID:</strong></td>
                                <td style="padding:8px; border-bottom:1px solid #ddd;">{job_id}</td></tr>
                            <tr><td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Agent:</strong></td>
                                <td style="padding:8px; border-bottom:1px solid #ddd;">{agent['name']}</td></tr>
                            <tr><td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Status:</strong></td>
                                <td style="padding:8px; border-bottom:1px solid #ddd;">Completed</td></tr>
                        </table>
                        <p>Your output files are ready for download on the platform.</p>
                        <p style="color:#666; font-size:12px;">This is an automated message from Honasa Flow Hub.</p>
                    </div>
                </body></html>
                """
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Job Completed: {agent['name']}"
                msg["From"] = SMTP_EMAIL
                msg["To"] = user_email
                msg.attach(MIMEText(html_content, "html"))

                def send_smtp():
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
                        server.sendmail(SMTP_EMAIL, user_email, msg.as_string())

                await asyncio.to_thread(send_smtp)
                logger.info(f"Email sent to {user_email} for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")

        # Cleanup temp config
        if job_config_path.exists():
            job_config_path.unlink()

        logger.info(f"Job {job_id} completed successfully")

    except subprocess.TimeoutExpired:
        logger.error(f"Job {job_id} timed out")
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error_message": "Script execution timed out (30 min limit)",
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
