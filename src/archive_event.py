import os
import json
import hmac
import hashlib
import logging

import boto3

from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource('s3')
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
GITHUB_SECRET = os.getenv('GITHUB_SECRET').encode('utf8')

def s3_key_name(event):
    headers = event['headers']
    now = datetime.utcnow()
    return '{org}/{now:%Y}/{now:%m}/{now:%d}/{event_type}/{event_id}'.format(
        org=event['pathParameters']['orgname'],
        now=now,
        event_type=headers['X-GitHub-Event'],
        event_id=headers['X-GitHub-Delivery'],
    )

def validate_signature(body, signature):
    github_hmac = hmac.new(GITHUB_SECRET, msg=body, digestmod=hashlib.sha1)
    hex_digest = "sha1={}".format(github_hmac.hexdigest())
    return len(hex_digest) == len(signature) and hmac.compare_digest(hex_digest, signature)

def lambda_handler(event, context):
    body = event['body']
    github_signature = event['headers']['X-Hub-Signature']
    if validate_signature(body.encode('utf8'), github_signature):
        logger.info("Successfully validated MAC")
        s3.Object(BUCKET_NAME, s3_key_name(event)).put(Body=body)
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'OK'})
        }
    else:
        logger.warn("Invalid MAC")
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'Forbidden'})
        }
