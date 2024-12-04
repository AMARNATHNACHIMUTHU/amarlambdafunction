import logging
from actions import check_alarm_tag, process_alarm_tags, delete_alarms, process_lambda_alarms
from os import getenv
##==================================================================##
# Author: Julio E Zegarra &  Manasa Maddi                            #        
# Version: 2.0.0                                                     #
# Date: Feb '2022                                                    #
# Purpose: Triggers Cloudwatch Alarms For All Types of Instances     #
##==================================================================##
logger = logging.getLogger()
logger.info(f"Value we Got for ALARM_TAG Env Variable: : {getenv('ALARM_TAG', 'MonitoringEnabled').lower()}")
logger.info(f"Does ALARM_TAG Key Exists and the Value is MonitoringEnabled? : {'Yes and Yes' if getenv('ALARM_TAG') and getenv('ALARM_TAG', 'MonitoringEnabled').lower() == 'MonitoringEnabled'.lower() else 'Does Not Exist'}")
alarm_tag = getenv('ALARM_TAG', 'MonitoringEnabled') \
                    if getenv('ALARM_TAG') \
                    and getenv('ALARM_TAG', 'MonitoringEnabled').lower() == "MonitoringEnabled".lower() \
                    else "MonitoringEnabled"
                
##alarm_tag = alarm_tag[0].lower() + alarm_tag[1:] if alarm_tag[0].isupper() else alarm_tag[0].upper() + alarm_tag[1:]
logger.info(f'Environment Variable Value for ALARM_TAG key is: {alarm_tag}')
create_alarm_tag_values = getenv("ALARM_TAG_VALUES").split(",")
cw_namespace = getenv("CLOUDWATCH_NAMESPACE", "CWAgent")
create_default_alarms_flag = getenv("CREATE_DEFAULT_ALARMS", "true").lower()
#append_dimensions = getenv("CLOUDWATCH_APPEND_DIMENSIONS", 'InstanceId, ImageId, InstanceType')
append_dimensions = getenv("CLOUDWATCH_APPEND_DIMENSIONS", 'InstanceId')
append_dimensions = [dimension.strip() for dimension in append_dimensions.split(',')]
alarm_cpu_high_default_threshold = getenv("ALARM_CPU_HIGH_THRESHOLD", "95")
alarm_status_check_threshold = getenv("ALARM_STATUS_CHECK_THRESHOLD", "1")
alarm_credit_balance_low_default_threshold = getenv("ALARM_CPU_CREDIT_BALANCE_LOW_THRESHOLD", "100")
alarm_memory_high_default_threshold = getenv("ALARM_MEMORY_HIGH_THRESHOLD", "90")
alarm_disk_space_percent_free_threshold = getenv("ALARM_DISK_PERCENT_LOW_THRESHOLD", "5")
alarm_disk_space_percent_free_varlogaudit_threshold = getenv("ALARM_VARLOGAUDIT_DISK_PERCENT_LOW_THRESHOLD", "5")
alarm_swap_high_threshold = getenv("ALARM_SWAP_HIGH_THRESHOLD", "10")
alarm_paging_file_high_threshold = getenv("ALARM_PAGING_FILE_HIGH_THRESHOLD", "90")
alarm_disk_used_percent_threshold = 100 - int(alarm_disk_space_percent_free_threshold)
alarm_disk_used_percent_varlogaudit_threshold = 100 - int(alarm_disk_space_percent_free_varlogaudit_threshold)
alarm_lambda_error_threshold = getenv("ALARM_LAMBDA_ERROR_THRESHOLD", "1")
alarm_lambda_throttles_threshold = getenv("ALARM_LAMBDA_THROTTLE_THRESHOLD", "1")
alarm_lambda_dead_letter_error_threshold = getenv("ALARM_LAMBDA_DEAD_LETTER_ERROR_THRESHOLD", "1")
alarm_lambda_destination_delivery_failure_threshold = getenv("ALARM_LAMBDA_DESTINATION_DELIVERY_FAILURE_THRESHOLD", "1")
sns_topic_arn = getenv("DEFAULT_ALARM_SNS_TOPIC_ARN", None)
crit_sns_topic_arn = getenv("CRITICAL_ALARM_SNS_TOPIC_ARN", None)
second_topic_arn = getenv("EMAIL_ALARM_SNS_TOPIC_ARN", None)
alarm_separator = '@'
alarm_identifier = 'AutoAlarm'
# For Redhat, the default device is xvda2, xfs, for Ubuntu, the default fstype is ext4,
# for Amazon Linux, the default device is xvda1, xfs
default_alarms = {
    'AWS/EC2': [
        {
            'Key': alarm_separator.join(
                [alarm_identifier, 'AWS/EC2', 'CPUUtilization', 'GreaterThanThreshold', '20m', 'Average']),
            'Value': alarm_cpu_high_default_threshold
        },
        {
            'Key': alarm_separator.join(
                [alarm_identifier, 'AWS/EC2', 'StatusCheckFailed', 'GreaterThanThreshold', '5m', 'Minimum']),
            'Value': alarm_status_check_threshold
        }
        ##{
        ##    'Key': alarm_separator.join(
        ##        [alarm_identifier, 'AWS/EC2', 'CPUCreditBalance', 'LessThanThreshold', '5m', 'Average']),
        ##    'Value': alarm_credit_balance_low_default_threshold
        ##}
    ],
    'AWS/Lambda': [
        {
            'Key': alarm_separator.join(
                [alarm_identifier, 'AWS/Lambda', 'Errors', 'GreaterThanThreshold', '5m', 'Average']),
            'Value': alarm_lambda_error_threshold
        },
        {
            'Key': alarm_separator.join(
                [alarm_identifier, 'AWS/Lambda', 'Throttles', 'GreaterThanThreshold', '5m', 'Average']),
            'Value': alarm_lambda_throttles_threshold
        }
    ],
    cw_namespace: {
        'Windows': [
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'LogicalDisk % Free Space', 'objectname', 'LogicalDisk',
                     'instance', 'C:', 'LessThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_space_percent_free_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'LogicalDisk % Free Space', 'objectname', 'LogicalDisk',
                     'instance', 'E:', 'LessThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_space_percent_free_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'LogicalDisk % Free Space', 'objectname', 'LogicalDisk',
                     'instance', 'F:', 'LessThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_space_percent_free_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'Paging File % Usage', 'objectname', 'Paging File',
                     'instance', '\??\C:\pagefile.sys', 'GreaterThanThreshold', '10m', 'Average']),
                'Value': alarm_paging_file_high_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'Memory % Committed Bytes In Use', 'objectname', 'Memory',
                     'instance', 'GreaterThanThreshold', '10m', 'Average']),
                'Value': alarm_memory_high_default_threshold
            }
        ],
        'Amazon Linux': [
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'xvda1', 'fstype', 'xfs', 'path',
                     '/', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'mem_used_percent', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_memory_high_default_threshold
            }
        ],
        'Red Hat': [
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'nvme0n1p2', 'fstype', 'xfs', 'path',
                     '/', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/appsvg-apps', 'fstype', 'xfs', 'path',
                     '/apps', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/productsvg-products', 'fstype', 'xfs', 'path',
                     '/products', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-tmp', 'fstype', 'xfs', 'path',
                     '/tmp', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-var', 'fstype', 'xfs', 'path',
                     '/var', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-varlog', 'fstype', 'xfs', 'path',
                     '/var/log', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-varlogaudit', 'fstype', 'xfs', 'path',
                     '/var/log/audit', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_varlogaudit_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-home', 'fstype', 'xfs', 'path',
                     '/home', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-opt', 'fstype', 'xfs', 'path',
                     '/opt', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'mapper/systemvg-optcontrolm', 'fstype', 'xfs', 'path',
                     '/opt/controlm', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'swap_used_percent', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_swap_high_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'mem_used_percent', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_memory_high_default_threshold
            }
        ],
        'Ubuntu': [
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'xvda1', 'fstype', 'ext4', 'path',
                     '/', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'mem_used_percent', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_memory_high_default_threshold
            }
        ],
        'SUSE': [
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'disk_used_percent', 'device', 'xvda1', 'fstype', 'xfs', 'path',
                     '/', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_disk_used_percent_threshold
            },
            {
                'Key': alarm_separator.join(
                    [alarm_identifier, cw_namespace, 'mem_used_percent', 'GreaterThanThreshold', '5m', 'Average']),
                'Value': alarm_memory_high_default_threshold
            }
        ]
    }
}
metric_dimensions_map = {
    cw_namespace: append_dimensions,
    'AWS/EC2': ['InstanceId']
}
def lambda_handler(event, context):
    logger.info(f'Event Received: {event}')
    
    try:
        if 'source' in event and event['source'] == 'aws.ec2' and event['detail']['state'] == 'running':
            instance_id = event['detail']['instance-id']
            logger.info(f'instance_id: {instance_id}')
            
            # determine if instance is tagged to create an alarm
            instance_info = check_alarm_tag(instance_id, alarm_tag, create_alarm_tag_values)
            # instance has been tagged for alarming, confirm an alarm doesn't already exist
            if instance_info:
                process_alarm_tags(instance_id, instance_info, default_alarms, metric_dimensions_map, sns_topic_arn, cw_namespace, create_default_alarms_flag, alarm_separator)
        elif 'source' in event and event['source'] == 'aws.ec2' and event['detail']['state'] == 'terminated':
            instance_id = event['detail']['instance-id']
            result = delete_alarms(instance_id)
    except Exception as e:
        # If any other exceptions which we didn't expect are raised
        # then fail the job and log the exception message.
        logger.error('Failure creating alarm: {}'.format(e))
        raise
