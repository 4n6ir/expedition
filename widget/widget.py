import boto3
import os

def handler(event, context):
    
    s3 = boto3.client('s3')
    
    result = s3.get_object(Bucket = os.environ['BUCKET'], Key = event['folder']+'/expedition.html')
    
    return result['Body'].read().decode()