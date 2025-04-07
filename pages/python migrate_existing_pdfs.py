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
        items = response.get("Items", [])

        for item in items:
            if "pdf_files" in item:
                normalized_files = normalize_pdf_files(item["pdf_files"], item.get("u_id"))
                
                if normalized_files != item["pdf_files"]:
                    update_user_pdf_files(item, normalized_files)

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    print("Data migration complete.")


def normalize_pdf_files(pdf_list, u_id):
    updated_pdf_files = []

    for pdf in pdf_list:
        if isinstance(pdf, dict) and "size" in pdf:
            updated_pdf_files.append(normalize_size_field(pdf, u_id))
        elif isinstance(pdf, dict) and "M" in pdf:
            updated_pdf_files.append(normalize_map_structure(pdf, u_id))
        elif isinstance(pdf, dict) and "N" in pdf:
            print(f"Warning: Removed unexpected Number entry from pdf_files for user {u_id}")
        else:
            updated_pdf_files.append(pdf)

    return updated_pdf_files


def normalize_size_field(pdf, u_id):
    try:
        if isinstance(pdf["size"], (float, int, str)):
            pdf["size"] = Decimal(str(pdf["size"]))
    except Exception:
        print(f"Warning: Could not convert size to Decimal for user {u_id}, file: {pdf.get('filename')}")
        pdf["size"] = Decimal("0")
    return pdf


def normalize_map_structure(pdf, u_id):
    file_data = pdf["M"]
    try:
        if "size" in file_data and "N" in file_data["size"]:
            file_data["size"] = {"N": str(Decimal(file_data["size"]["N"]))}
    except Exception:
        print(f"Warning: Could not convert size in map for user {u_id}, file: {file_data.get('filename', {}).get('S')}")
        file_data["size"] = {"N": "0"}
    return {"M": file_data}


def update_user_pdf_files(user_item, updated_pdf_files):
    try:
        user_table.update_item(
            Key={"u_id": user_item["u_id"], "u_email": user_item["u_email"]},
            UpdateExpression="SET pdf_files = :pdf",
            ExpressionAttributeValues={":pdf": updated_pdf_files}
        )
        print(f"✅ Updated user: {user_item.get('u_id')}")
    except Exception as e:
        print(f"❌ Error updating user {user_item.get('u_id')}: {e}")

if __name__ == "__main__":
    migrate_user_data()