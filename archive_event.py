import os
import json
import boto3
import logging

from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')
bucket_name = os.getenv('S3_BUCKET_NAME')

def s3_key_name(event):
    headers = event['headers']
    now = datetime.utcnow()
    return '{org}/{now:%Y}/{now:%m}/{now:%d}/{event_type}/{event_id}'.format(
        org=event['pathParameters']['orgname'],
        now=now,
        event_type=headers['X-GitHub-Event'],
        event_id=headers['X-GitHub-Delivery'],
    )



def lambda_handler(event, context):
    logger.info("Event: " + str(event))
    logger.info("Context: " + str(context))

    s3.Object(bucket_name, s3_key_name(event)).put(Body=event['body'])
    return {
        'statusCode': 200,
        'headers': { 'Content-Type': 'application/json' },
        'body': json.dumps({ 'status': 'OK'})
    }
