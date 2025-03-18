import streamlit as st
import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_REGION_S3 = os.getenv("AWS_REGION_S3")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE = os.getenv("USER_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

# Sector options
SECTOR_CHOICES = [
    "Technology", "Healthcare", "Finance", "Energy",
    "Education", "Manufacturing", "Retail"
]

# Initialize AWS Clients
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION_DYNAMO,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION_S3,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    """Fetch all users from DynamoDB."""
    try:
        response = user_table.scan()
        return response.get("Items", [])
    except ClientError as e:
        st.error(f"Error fetching users: {str(e)}")
        return []

def update_user_data(user_id, user_email, new_password, approval_status, pdf_limit):
    """Update user data in DynamoDB."""
    try:
        update_expr = []
        expr_values = {}

        if new_password:
            update_expr.append("u_password = :new_pwd")
            expr_values[":new_pwd"] = new_password

        update_expr.append("is_approved = :approval")
        expr_values[":approval"] = approval_status

        update_expr.append("pdf_limit = :pdf_limit")
        expr_values[":pdf_limit"] = int(pdf_limit)

        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeValues=expr_values
        )
        st.success(f"User {user_email} updated successfully!")
        st.rerun()
    except ClientError as e:
        st.error(f"Error updating user: {str(e)}")

def upload_pdf(file, user_id, user_email, pdf_limit, sector):
    """Upload PDF with sector metadata to S3 and DynamoDB."""
    try:
        # Generate unique file key with timestamp
        timestamp = datetime.now().timestamp()
        file_key = f"users/{user_id}/{timestamp}_{file.name}"
        
        # Debug: Show upload parameters
        st.write("## Debug Information")
        st.write(f"Uploading for user: {user_id} ({user_email})")
        st.write(f"Selected sector: {sector}")
        st.write(f"File name: {file.name}")
        st.write(f"Temporary file key: {file_key}")
        
        # Get current user data
        st.write("Fetching current user data...")
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})
        pdf_list = user_data.get("pdf_files", [])
        
        # Validate upload limit
        st.write(f"Current PDF count: {len(pdf_list)}/{pdf_limit}")
        if len(pdf_list) >= int(pdf_limit):
            st.error(f"Upload limit reached! Maximum {pdf_limit} PDFs allowed")
            return

        # Upload to S3
        st.write("Starting S3 upload...")
        s3.upload_fileobj(
            Fileobj=file,
            Bucket=S3_BUCKET,
            Key=file_key,
            ExtraArgs={"ContentType": "application/pdf"}
        )
        st.write("S3 upload completed successfully!")
        
        # Create metadata object with sector
        pdf_metadata = {
            "file_key": file_key,
            "filename": file.name,
            "sector": sector,
            "upload_date": datetime.now().isoformat()
        }
        
        # Debug: Show complete metadata
        st.write("Prepared PDF metadata:", pdf_metadata)
        
        # Update DynamoDB
        st.write("Starting DynamoDB update...")
        response = user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = list_append(if_not_exists(pdf_files, :empty_list), :pdf)",
            ExpressionAttributeValues={
                ":pdf": [pdf_metadata],
                ":empty_list": []
            },
            ReturnValues="ALL_NEW"
        )
        
        # Show debug info
        st.write("DynamoDB Update Response:", response)
        
        # Verify update
        if 'Attributes' in response:
            st.success(f"PDF successfully uploaded to {sector} sector!")
            st.write("Verification - New PDF list:", response['Attributes'].get('pdf_files', []))
            st.rerun()
        else:
            st.error("Update failed - no attributes returned")
        
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        st.error(f"AWS API Error: {error_msg}")
        st.write("Full error details:", e.response)
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        st.write("Exception details:", repr(e))

def delete_pdf(user_id, user_email, file_key):
    """Delete PDF from S3 and DynamoDB."""
    try:
        st.write("Starting delete operation...")
        st.write(f"Deleting file: {file_key}")
        
        # Delete from S3
        s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        st.write("S3 deletion completed")
        
        # Update DynamoDB
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})
        pdf_list = user_data.get("pdf_files", [])
        
        # Create new list without the deleted PDF
        new_pdf_list = [pdf for pdf in pdf_list if pdf.get("file_key") != file_key]
        
        st.write("Updating DynamoDB with new PDF list:", new_pdf_list)
        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = :new_list",
            ExpressionAttributeValues={":new_list": new_pdf_list}
        )
        
        st.success("PDF deleted successfully!")
        st.rerun()
    except ClientError as e:
        st.error(f"Delete error: {e.response['Error']['Message']}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

def process_pdf_entries(pdf_files):
    """Convert legacy entries to modern format with sector."""
    processed = []
    for entry in pdf_files:
        if isinstance(entry, str):
            processed.append({
                "file_key": entry,
                "filename": entry.split("/")[-1],
                "sector": "Uncategorized",
                "upload_date": "2023-01-01T00:00:00"
            })
        else:
            entry["sector"] = entry.get("sector", "Uncategorized")
            processed.append(entry)
    return processed

def main():
    st.title("Document Management Admin Panel")
    
    # Add connection check
    try:
        user_table.table_status  # Simple connection check
    except Exception as e:
        st.error(f"Failed to connect to DynamoDB: {str(e)}")
        return
    
    users = fetch_users()
    if not users:
        st.warning("No registered users found.")
        return
    
    for user in users:
        with st.expander(f"User: {user['u_email']}", expanded=False):
            # Approval controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve {user['u_id']}"):
                    update_user_data(
                        user["u_id"], 
                        user["u_email"], 
                        None, 
                        True, 
                        user.get("pdf_limit", 5)
                    )
            with col2:
                if st.button(f"Disapprove {user['u_id']}"):
                    update_user_data(
                        user["u_id"], 
                        user["u_email"], 
                        None, 
                        False, 
                        user.get("pdf_limit", 5)
                    )

            # PDF management
            st.subheader("Document Management")
            current_limit = int(user.get("pdf_limit", 5))
            pdf_limit = st.number_input(
                "Maximum PDF Allocations",
                value=current_limit,
                min_value=1,
                max_value=20,
                key=f"limit_{user['u_id']}"
            )

            # File upload section
            st.write("### Upload New Document")
            upload_col, sector_col = st.columns([3, 2])
            with upload_col:
                uploaded_file = st.file_uploader(
                    "Select PDF File",
                    type=["pdf"],
                    key=f"upload_{user['u_id']}"
                )
            with sector_col:
                sector = st.selectbox(
                    "Document Sector",
                    SECTOR_CHOICES,
                    index=0,
                    key=f"sector_{user['u_id']}"
                )

            if uploaded_file:
                if st.button("Upload Document", key=f"upload_btn_{user['u_id']}"):
                    upload_pdf(uploaded_file, user["u_id"], user["u_email"], pdf_limit, sector)

            # Display existing documents
            if "pdf_files" in user:
                st.write("### Managed Documents")
                if st.button("Refresh List", key=f"refresh_{user['u_id']}"):
                    st.rerun()
                
                processed_pdfs = process_pdf_entries(user["pdf_files"])
                
                # Group by sector
                sector_groups = {}
                for pdf in processed_pdfs:
                    sector = pdf.get("sector", "Uncategorized")
                    sector_groups.setdefault(sector, []).append(pdf)

                # Display documents
                for sector, docs in sector_groups.items():
                    st.write(f"#### {sector} Sector ({len(docs)} documents)")
                    for doc in docs:
                        col1, col2, col3 = st.columns([4, 3, 2])
                        with col1:
                            st.markdown(f"**File Name:** `{doc['filename']}`")
                        with col2:
                            upload_time = pd.to_datetime(doc['upload_date']).strftime('%Y-%m-%d %H:%M')
                            st.markdown(f"**Uploaded:** {upload_time}")
                        with col3:
                            url = s3.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': S3_BUCKET, 'Key': doc['file_key']},
                                ExpiresIn=3600
                            )
                            st.markdown(f"[Download PDF]({url})")
                            if st.button("Delete", key=f"del_{doc['file_key']}"):
                                delete_pdf(user["u_id"], user["u_email"], doc['file_key'])
                    st.markdown("---")

if __name__ == "__main__":
    main()