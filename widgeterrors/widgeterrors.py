import boto3
import os

def handler(event, context):
    
    s3 = boto3.client('s3')
    
    result = s3.get_object(Bucket = os.environ['BUCKET'], Key = 'errors/expedition.html')
    
    return result['Body'].read().decode()