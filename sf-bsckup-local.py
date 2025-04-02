import pandas as pd
from simple_salesforce import Salesforce
import os
import time
import boto3

USERNAME = os.getenv("SF_USERNAME")
PASSWORD = os.getenv("SF_PASSWORD")
SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN")
DOMAIN = os.getenv("SF_DOMAIN", "login")  # Default to "login"
S3_BUCKET = os.getenv("S3_BUCKET_NAME")  # S3 bucket name
S3_FOLDER = os.getenv("S3_FOLDER", "salesforce_backup")  # Folder in S3
EXPORT_DIR = "./salesforce_full_backup"

sf = Salesforce(
    username=USERNAME,
    password=PASSWORD,
    security_token=SECURITY_TOKEN,
    domain=DOMAIN
)

if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

s3_client = boto3.client("s3")

print("Fetching object list...")
describe = sf.describe()
sobjects = [s['name'] for s in describe['sobjects'] if s['queryable'] and not s['deprecatedAndHidden']]

print(f"Found {len(sobjects)} queryable objects.")

for obj in sobjects:
    try:
        print(f"\nExporting {obj}...")
        obj_desc = sf.__getattr__(obj).describe()
        fields = [f['name'] for f in obj_desc['fields']]
        field_str = ", ".join(fields)

        query = f"SELECT {field_str} FROM {obj} LIMIT 50000"
        data = sf.query_all(query)
        records = data['records']

        for rec in records:
            rec.pop('attributes', None)

        df = pd.DataFrame(records)
        file_path = f"{EXPORT_DIR}/{obj}.csv"
        df.to_csv(file_path, index=False)
        print(f"{obj} export done. Records: {len(records)}")

        s3_path = f"{S3_FOLDER}/{obj}.csv"
        s3_client.upload_file(file_path, S3_BUCKET, s3_path)
        print(f" Uploaded {obj}.csv to s3://{S3_BUCKET}/{s3_path}")

        time.sleep(2)  # Avoid API rate limits

    except Exception as e:
        print(f"⚠️ Failed to export {obj}: {str(e)}")

print("\n Full Backup Completed!")
