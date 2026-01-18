"""
Notification utilities for Airflow DAGs
"""
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def task_failure_alert(context: Dict[str, Any]):
    """
    Send alert when task fails.
    This function is called automatically by Airflow on task failure.
    """
    task_instance = context['task_instance']
    dag_id = context['dag'].dag_id
    task_id = task_instance.task_id
    execution_date = context['execution_date']
    exception = context.get('exception')
    
    # Log the failure
    logger.error(f"""
    ════════════════════════════════════════════════════════════════
    TASK FAILURE ALERT
    ════════════════════════════════════════════════════════════════
    DAG: {dag_id}
    Task: {task_id}
    Execution Date: {execution_date}
    Exception: {exception}
    ════════════════════════════════════════════════════════════════
    """)
    
    # Here you can add email, Slack, or other notification methods
    # Example: send_email_alert(context)
    # Example: send_slack_alert(context)


def task_retry_alert(context: Dict[str, Any]):
    """
    Send alert when task is retried.
    """
    task_instance = context['task_instance']
    task_id = task_instance.task_id
    
    logger.warning(f"""
    ════════════════════════════════════════════════════════════════
    TASK RETRY ALERT
    ════════════════════════════════════════════════════════════════
    Task: {task_id}
    Retry Number: {task_instance.try_number}
    Max Retries: {task_instance.max_tries}
    ════════════════════════════════════════════════════════════════
    """)


def dag_success_alert(context: Dict[str, Any]):
    """
    Send alert when entire DAG succeeds.
    """
    dag_id = context['dag'].dag_id
    execution_date = context['execution_date']
    
    logger.info(f"""
    ════════════════════════════════════════════════════════════════
    DAG SUCCESS
    ════════════════════════════════════════════════════════════════
    DAG: {dag_id}
    Execution Date: {execution_date}
    Status: ✓ COMPLETED SUCCESSFULLY
    ════════════════════════════════════════════════════════════════
    """)


def send_email_alert(context: Dict[str, Any]):
    """
    Send email notification (requires SMTP configuration).
    """
    from airflow.utils.email import send_email
    
    task_instance = context['task_instance']
    dag_id = context['dag'].dag_id
    task_id = task_instance.task_id
    execution_date = context['execution_date']
    exception = context.get('exception')
    
    subject = f"[AIRFLOW ALERT] {dag_id} - {task_id} Failed"
    
    html_content = f"""
    <h2>Airflow Task Failure</h2>
    <p><strong>DAG:</strong> {dag_id}</p>
    <p><strong>Task:</strong> {task_id}</p>
    <p><strong>Execution Date:</strong> {execution_date}</p>
    <p><strong>Exception:</strong> {exception}</p>
    <p><strong>Log URL:</strong> {task_instance.log_url}</p>
    """
    
    try:
        send_email(
            to=['your-email@example.com'],
            subject=subject,
            html_content=html_content
        )
        logger.info("✓ Email alert sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email alert: {str(e)}")


def send_slack_alert(context: Dict[str, Any]):
    """
    Send Slack notification (requires Slack webhook).
    """
    import requests
    import json
    
    # Load Slack webhook URL from config
    # webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    
    task_instance = context['task_instance']
    dag_id = context['dag'].dag_id
    task_id = task_instance.task_id
    execution_date = context['execution_date']
    
    message = {
        "text": f"🚨 *Airflow Task Failed*",
        "attachments": [
            {
                "color": "danger",
                "fields": [
                    {"title": "DAG", "value": dag_id, "short": True},
                    {"title": "Task", "value": task_id, "short": True},
                    {"title": "Execution Date", "value": str(execution_date), "short": False},
                ]
            }
        ]
    }
    
    # Uncomment when you have a webhook URL
    # try:
    #     response = requests.post(webhook_url, json=message)
    #     if response.status_code == 200:
    #         logger.info("✓ Slack alert sent successfully")
    # except Exception as e:
    #     logger.error(f"Failed to send Slack alert: {str(e)}")


def get_task_duration(context: Dict[str, Any]) -> float:
    """
    Calculate task duration in seconds.
    """
    task_instance = context['task_instance']
    
    if task_instance.start_date and task_instance.end_date:
        duration = (task_instance.end_date - task_instance.start_date).total_seconds()
        return duration
    
    return 0.0


def log_task_performance(context: Dict[str, Any]):
    """
    Log task performance metrics.
    """
    task_instance = context['task_instance']
    task_id = task_instance.task_id
    duration = get_task_duration(context)
    
    logger.info(f"""
    ════════════════════════════════════════════════════════════════
    TASK PERFORMANCE
    ════════════════════════════════════════════════════════════════
    Task: {task_id}
    Duration: {duration:.2f} seconds
    Try Number: {task_instance.try_number}
    ════════════════════════════════════════════════════════════════
    """)
