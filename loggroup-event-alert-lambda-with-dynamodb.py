# Efficient AWS Lambda Error Notification System with DynamoDB and SNS

## Overview
This blog explains an AWS Lambda function designed to process CloudWatch log events, identify and analyze error messages, and send email alerts using Amazon SNS (Simple Notification Service). The solution integrates DynamoDB for tracking email notifications to prevent redundant alerts and leverages EC2 instance tags for enabling or disabling notifications dynamically.

## What Does This Task Do?
This Lambda function:
1. Processes CloudWatch logs to identify error events.
2. Extracts critical information such as the instance ID and error details.
3. Verifies if the instance is configured for error notifications by checking EC2 tags.
4. Checks the last email notification timestamp from DynamoDB to avoid sending repeated alerts within a short interval.
5. Sends email notifications for new error events via Amazon SNS.
6. Updates DynamoDB with the latest notification timestamp.

## By automating this workflow, the function ensures that errors are detected and addressed promptly while avoiding alert fatigue caused by duplicate notifications.

## Code Breakdown

### Initialization and Setup

import json
import boto3
import gzip
import base64
import logging
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
ec2 = boto3.client('ec2')

# Environment variables
sns_topic_arn = os.environ['SNS_TOPIC_ARN']
dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']
exception_table = dynamodb.Table(dynamodb_table_name)

## This part of the code sets up logging and initializes AWS service clients for SNS, DynamoDB, and EC2. It also retrieves environment variables for SNS Topic ARN and DynamoDB table name, making the solution dynamic and configurable.

### Log Decoding and Error Extraction

def lambda_handler(event, context):
    try:
        logger.info("Decoding and decompressing log data...")
        log_data = base64.b64decode(event['awslogs']['data'])
        log_data = gzip.decompress(log_data)
        decoded_data = json.loads(log_data)
        log_stream = decoded_data['logStream']
        log_events = decoded_data['logEvents']
    except Exception as e:
        logger.error(f"Error in decoding and decompressing log data: {e}")
        raise e

    instance_id = extract_instance_id_from_log_stream(log_stream)
    if not instance_id:
        logger.error(f"No instance ID found in log stream '{log_stream}'")
        return {'statusCode': 400, 'body': json.dumps("Instance ID not found.")}

    if not log_events:
        logger.info("No log events found.")
        return {'statusCode': 200, 'body': json.dumps("No log events to process.")}

    most_recent_log_message = log_events[-1]['message']
    logger.info(f"Most recent log message: {most_recent_log_message}")

## The Lambda handler extracts and processes CloudWatch log data. It ensures that logs are decompressed and decoded correctly and retrieves the most recent log event.

### Notification Logic
#### Extracting Instance ID and Validating Alerts

def extract_instance_id_from_log_stream(log_stream):
    return log_stream  # Update this logic if the log stream has a specific format for instance IDs

def check_alert_enabled(instance_id):
    tags = ec2.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [instance_id]}, {'Name': 'key', 'Values': ['AlertEnabled']}])
    for tag in tags.get('Tags', []):
        if tag['Key'] == 'AlertEnabled' and tag['Value'].lower() == 'true':
            return True
    return False

## The `extract_instance_id_from_log_stream` function isolates the instance ID from the log stream name. The `check_alert_enabled` function ensures that notifications are only sent if the instance is tagged with `AlertEnabled=true`.

#### Sending Notifications

def process_alert(log_message, instance_id, subject):
    try:
        response = sns.publish(TopicArn=sns_topic_arn, Message=log_message, Subject=subject)
        logger.info(f"Notification sent. Response: {response}")
    except ClientError as e:
        logger.error(f"Failed to send notification: {e}")

## If alerts are enabled, the function constructs a subject and sends an email via SNS. Errors during this process are logged for troubleshooting.

#### Preventing Duplicate Alerts

def get_last_email_timestamp(instance_id):
    response = exception_table.query(KeyConditionExpression=Key('EC2Id').eq(instance_id), Limit=1, ScanIndexForward=False)
    if 'Items' in response and len(response['Items']) > 0:
        return response['Items'][0].get('LastEmailTimestamp')
    return None

def within_last_n_minutes(last_timestamp, minutes):
    datetime_format = "%Y-%m-%d %H:%M:%S"
    if not last_timestamp:
        return False
    last_email_timestamp = datetime.strptime(last_timestamp, datetime_format)
    current_timestamp = datetime.now()
    return (current_timestamp - last_email_timestamp) < timedelta(minutes=minutes)

if within_last_n_minutes(last_email_timestamp, 5):
    logger.info(f"Skipping email notification for instance {instance_id} as it was sent recently.")
    return {'statusCode': 200, 'body': json.dumps("Email notification already sent recently.")}

## The DynamoDB table tracks the timestamp of the last notification. The `within_last_n_minutes` function compares the current time with the last notification timestamp to avoid sending redundant alerts within a 5-minute interval.

## Key Features and Benefits
- Automated Error Notification: Detects errors in logs and sends alerts promptly.
- Dynamic Configuration: Uses EC2 instance tags to enable or disable alerts.
- Duplication Prevention: Tracks and limits redundant notifications with DynamoDB.
- Scalable and Cost-Efficient: Runs in a serverless environment, leveraging AWS Lambda for on-demand execution.

## Conclusion
This AWS Lambda function provides a robust mechanism for monitoring and alerting on EC2 instance logs. By combining CloudWatch, DynamoDB, and SNS, it ensures timely notification of critical errors while minimizing unnecessary alerts.
