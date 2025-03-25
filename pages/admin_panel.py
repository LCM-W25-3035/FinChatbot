import streamlit as st
import boto3
import os
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE = os.getenv("USER_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

SECTOR_CHOICES = ["Technology", "Healthcare", "Finance", "Education", "Other"]

# Initialize AWS clients
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION_DYNAMO,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
s3 = boto3.client("s3")
user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    try:
        return user_table.scan().get("Items", [])
    except ClientError as e:
        st.error(f"Error fetching users: {str(e)}")
        return []

def process_pdf_entries(pdf_files):
    processed = []
    for entry in pdf_files:
        if isinstance(entry, str):
            # Handle legacy format
            sector = "Other"
            if "/" in entry:
                parts = entry.split("/")
                if len(parts) >= 3 and parts[2] in SECTOR_CHOICES:
                    sector = parts[2]
            processed.append({
                "file_key": entry,
                "filename": entry.split("/")[-1],
                "sector": sector,
                "upload_date": "2023-01-01T00:00:00",
                "size": 0,
                "storage_class": "STANDARD"
            })
        else:
            entry.setdefault("sector", "Other")
            entry.setdefault("upload_date", datetime.now().isoformat())
            entry.setdefault("size", 0)
            entry.setdefault("storage_class", "STANDARD")
            processed.append(entry)
    return processed

def upload_pdf(file, user_id, user_email, pdf_limit, sector):
    try:
        timestamp = datetime.now().timestamp()
        # New sector-based path
        file_key = f"users/{user_id}/{sector}/{timestamp}_{file.name}"
        
        # Upload with metadata and tags
        s3.upload_fileobj(
            file, S3_BUCKET, file_key,
            ExtraArgs={
                "ContentType": "application/pdf",
                "Metadata": {"sector": sector},
                "Tagging": f"sector={sector}"
            }
        )
        
        pdf_metadata = {
            "file_key": file_key,
            "filename": file.name,
            "sector": sector,
            "upload_date": datetime.now().isoformat(),
            "size": file.size,
            "storage_class": "STANDARD"
        }
        
        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = list_append(if_not_exists(pdf_files, :empty_list), :pdf)",
            ExpressionAttributeValues={
                ":pdf": [pdf_metadata],
                ":empty_list": []
            }
        )
        st.success(f"PDF uploaded to {sector} sector!")
        st.rerun()
    except Exception as e:
        st.error(f"Upload error: {str(e)}")

def delete_pdf(user_id, user_email, file_key):
    try:
        # Delete from S3
        s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        
        # Update DynamoDB
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})
        pdf_list = process_pdf_entries(user_data.get("pdf_files", []))
        
        new_pdf_list = [pdf for pdf in pdf_list if pdf["file_key"] != file_key]
        
        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = :new_list",
            ExpressionAttributeValues={":new_list": new_pdf_list}
        )
        st.success("PDF deleted successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Delete error: {str(e)}")

def migrate_existing_files():
    """Admin function to add sector organization to existing files"""
    if st.button("Migrate Existing Files to Sector Structure"):
        users = fetch_users()
        for user in users:
            user_id = user["u_id"]
            pdf_files = process_pdf_entries(user.get("pdf_files", []))
            
            for pdf in pdf_files:
                try:
                    # Get current file details
                    old_key = pdf["file_key"]
                    sector = pdf.get("sector", "Other")
                    
                    # New sector-based path
                    new_key = f"users/{user_id}/{sector}/{old_key.split('/')[-1]}"
                    
                    # Copy file to new location
                    s3.copy_object(
                        Bucket=S3_BUCKET,
                        CopySource={"Bucket": S3_BUCKET, "Key": old_key},
                        Key=new_key,
                        Metadata={"sector": sector},
                        Tagging=f"sector={sector}",
                        MetadataDirective="REPLACE"
                    )
                    
                    # Delete old file
                    s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
                    
                    # Update DynamoDB record
                    user_table.update_item(
                        Key={"u_id": user_id, "u_email": user["u_email"]},
                        UpdateExpression="SET pdf_files = :new_list",
                        ExpressionAttributeValues={
                            ":new_list": [{**pdf, "file_key": new_key}]
                        }
                    )
                    
                except Exception as e:
                    st.error(f"Migration failed for {old_key}: {str(e)}")
        st.success("Migration completed!")

def handle_pdf_management(users):
    selected_user = st.selectbox("Select user", 
                               [(u['u_id'], u['u_email']) for u in users], 
                               format_func=lambda x: x[1])
    
    if selected_user:
        user_id, user_email = selected_user
        user_data = user_table.get_item(Key={"u_id": user_id, "u_email": user_email}).get("Item", {})
        pdf_files = process_pdf_entries(user_data.get("pdf_files", []))
        
        # Upload section
        with st.form("upload_form"):
            col1, col2 = st.columns([3, 2])
            with col1:
                uploaded_file = st.file_uploader("PDF File", type=["pdf"])
            with col2:
                sector = st.selectbox("Sector", SECTOR_CHOICES, index=4)
            
            if st.form_submit_button("Upload"):
                if len(pdf_files) >= user_data.get("pdf_limit", 5):
                    st.error("Upload limit reached!")
                elif uploaded_file:
                    upload_pdf(uploaded_file, user_id, user_email, 
                              user_data.get("pdf_limit", 5), sector)
                else:
                    st.warning("Please select a PDF file")

        # Display section
        st.subheader("Managed Documents")
        if pdf_files:
            for pdf in pdf_files:
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                with col1:
                    st.write(pdf['filename'])
                with col2:
                    st.write(pdf['sector'])
                with col3:
                    st.write(pd.to_datetime(pdf['upload_date']).strftime('%Y-%m-%d %H:%M'))
                with col4:
                    st.write(f"{pdf['size']/1024/1024:.1f} MB")
                with col5:
                    if st.button("Delete", key=f"del_{pdf['file_key']}"):
                        delete_pdf(user_id, user_email, pdf['file_key'])
                st.markdown("---")
        else:
            st.info("No documents found")

def main():
    st.title("Document Management System")
    
    # Migration panel
    with st.expander("Admin Tools"):
        migrate_existing_files()
    
    users = fetch_users()
    if not users:
        st.warning("No users found in the system")
        return
    
    handle_pdf_management(users)

if __name__ == "__main__":
    main()