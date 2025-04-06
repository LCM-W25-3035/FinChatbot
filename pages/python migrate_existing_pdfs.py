import boto3
from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE_NAME = os.getenv("USER_TABLE")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION_DYNAMO,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
user_table = dynamodb.Table(USER_TABLE_NAME)

def migrate_user_data():
    print(f"Starting data migration for table: {USER_TABLE_NAME}")
    scan_kwargs = {}
    while True:
        response = user_table.scan(**scan_kwargs)

        for item in response.get("Items", []):
            if "pdf_files" in item:
                updated_pdf_files = []
                for pdf_info in item["pdf_files"]:
                    if isinstance(pdf_info, dict):
                        # Handle the case where pdf_info is a dictionary (likely the "M" structure)
                        if "size" in pdf_info:
                            if isinstance(pdf_info["size"], float):
                                pdf_info["size"] = Decimal(str(pdf_info["size"]))
                            elif isinstance(pdf_info["size"], (int, str)):
                                try:
                                    pdf_info["size"] = Decimal(str(pdf_info["size"]))
                                except ValueError:
                                    print(f"Warning: Could not convert size to Decimal for user {item.get('u_id')}, file: {pdf_info.get('filename')}")
                                    pdf_info["size"] = Decimal("0") # Set to a default Decimal if conversion fails
                        updated_pdf_files.append(pdf_info)
                    elif isinstance(pdf_info, dict) and "M" in pdf_info:
                        # Handle the DynamoDB Map structure explicitly
                        file_data = pdf_info["M"]
                        if "size" in file_data and "N" in file_data["size"]:
                            try:
                                file_data["size"] = {"N": str(Decimal(file_data["size"]["N"]))}
                            except ValueError:
                                print(f"Warning: Could not convert size to Decimal for user {item.get('u_id')}, file: {file_data.get('filename', {}).get('S')}")
                                file_data["size"] = {"N": "0"}
                        updated_pdf_files.append({"M": file_data})
                    elif isinstance(pdf_info, dict) and "N" in pdf_info:
                        # This is the inconsistent Number entry - remove it
                        print(f"Warning: Removed unexpected Number entry from pdf_files for user {item.get('u_id')}")
                    else:
                        updated_pdf_files.append(pdf_info) # Keep other valid entries

                if updated_pdf_files != item["pdf_files"]:
                    try:
                        user_table.update_item(
                            Key={"u_id": item["u_id"], "u_email": item["u_email"]},
                            UpdateExpression="SET pdf_files = :pdf",
                            ExpressionAttributeValues={":pdf": updated_pdf_files}
                        )
                        print(f"Updated user: {item.get('u_id')}")
                    except Exception as e:
                        print(f"Error updating user {item.get('u_id')}: {e}")

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break
    print("Data migration complete.")

if __name__ == "__main__":
    migrate_user_data()