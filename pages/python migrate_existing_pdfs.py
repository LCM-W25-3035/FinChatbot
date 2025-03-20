# migration_script.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_data():
    # Debug print environment variables
    print("AWS Region:", os.getenv("AWS_REGION_DYNAMO"))
    print("User Table:", os.getenv("USER_TABLE"))
    
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION_DYNAMO"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    try:
        table = dynamodb.Table(os.getenv("USER_TABLE"))
        print("Table exists! Proceeding...")
        
        response = table.scan()
        users = response['Items']
        
        for user in users:
            if 'pdf_files' in user:
                # Migration logic here
                print(f"Migrating user {user['u_email']}")
                
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Verify table name and AWS credentials")

if __name__ == "__main__":
    migrate_data()