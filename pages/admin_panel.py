import streamlit as st
import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_REGION_S3 = os.getenv("AWS_REGION_S3")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE = os.getenv("USER_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

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
    """Update user password, approval status, and PDF limit."""
    try:
        update_expression = []
        expression_values = {}

        if new_password:
            update_expression.append("u_pwd = :new_pwd")
            expression_values[":new_pwd"] = new_password

        update_expression.append("is_approved = :approval")
        expression_values[":approval"] = approval_status

        update_expression.append("pdf_limit = :pdf_limit")
        expression_values[":pdf_limit"] = pdf_limit

        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET " + ", ".join(update_expression),
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW"
        )
        st.success(f"User {user_email} updated successfully!")
        st.rerun()
    except ClientError as e:
        st.error(f"Error updating user: {str(e)}")

def upload_pdf(file, user_id, user_email, pdf_limit):
    """Upload PDF to S3 and update pdf_files list in DynamoDB."""
    try:
        file_key = f"{user_id}/{file.name}"

        # Fetch user data
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})
        
        # Check the current number of PDFs
        pdf_list = user_data.get("pdf_files", []) if "pdf_files" in user_data else []
        if len(pdf_list) >= pdf_limit:
            st.error(f"Upload limit reached! Max PDFs allowed: {pdf_limit}")
            return

        # Upload to S3
        s3.upload_fileobj(file, S3_BUCKET, file_key, ExtraArgs={"ContentType": "application/pdf"})
        pdf_list.append(file_key)

        # Update user with new PDF list
        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = :pdfs",
            ExpressionAttributeValues={":pdfs": pdf_list}
        )

        st.success(f"File '{file.name}' uploaded successfully!")
    except ClientError as e:
        st.error(f"Error uploading PDF: {str(e)}")

def delete_pdf(user_id, user_email, pdf_name):
    """Delete PDF from S3 and update pdf_files in DynamoDB."""
    try:
        file_key = f"{user_id}/{pdf_name}"
        s3.delete_object(Bucket=S3_BUCKET, Key=file_key)

        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})

        pdf_list = user_data.get("pdf_files", []) if "pdf_files" in user_data else []

        if file_key in pdf_list:
            pdf_list.remove(file_key)

            user_table.update_item(
                Key={"u_id": user_id, "u_email": user_email},
                UpdateExpression="SET pdf_files = :pdfs",
                ExpressionAttributeValues={":pdfs": pdf_list}
            )

        st.success(f"File '{pdf_name}' deleted successfully!")
        st.rerun()
    except ClientError as e:
        st.error(f"Error deleting PDF: {str(e)}")

# Refactored 'main()' to Reduce Cognitive Complexity per SonarQube

def main():
    st.title("Admin Panel - User Management")

    users = fetch_users()
    if not users:
        st.warning("No users found.")
        return

    st.subheader("Manage Users")
    for user in users:
        render_user_controls(user)

    st.subheader("Manage PDFs")
    handle_pdf_management(users)

def render_user_controls(user):
    """Display controls for managing individual users."""
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button(f"Approve {user['u_id']}", key=f"approve_{user['u_id']}"):
            update_user_data(user['u_id'], user['u_email'], None, True, user.get('pdf_limit', 5))
    with col2:
        if st.button(f"Disapprove {user['u_id']}", key=f"disapprove_{user['u_id']}"):
            update_user_data(user['u_id'], user['u_email'], None, False, user.get('pdf_limit', 5))
    with col3:
        render_user_edit_section(user)

def render_user_edit_section(user):
    """Provide editable fields for user properties."""
    with st.expander(f"Edit {user['u_email']}"):
        new_password = st.text_input("New Password", type="password", key=f"pwd_{user['u_id']}")
        new_approval = st.checkbox("Approved", value=user.get('is_approved', False), key=f"approval_{user['u_id']}")
        new_pdf_limit = st.number_input("PDF Limit", 1, 20, int(user.get('pdf_limit', 5)), key=f"limit_{user['u_id']}")

        if st.button("Save", key=f"save_{user['u_id']}"):
            update_user_data(user['u_id'], user['u_email'], new_password, new_approval, new_pdf_limit)

def handle_pdf_management(users):
    """Display controls for managing user PDFs."""
    selected_user = st.selectbox("Select user", [(u['u_id'], u['u_email']) for u in users])
    if selected_user:
        user_id, user_email = selected_user
        user_data = user_table.get_item(Key={"u_id": user_id, "u_email": user_email}).get("Item", {})
        pdf_files = user_data.get("pdf_files", [])
        pdf_limit = user_data.get("pdf_limit", 5)

        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file and st.button("Upload"):
            upload_pdf(uploaded_file, user_id, user_email, pdf_limit)

        st.write(f"Existing PDFs ({len(pdf_files)}/{pdf_limit}):")
        for pdf in pdf_files:
            if st.button("Delete", key=f"del_{pdf}"):
                delete_pdf(user_id, user_email, pdf.split("/")[-1])

if __name__ == "__main__":
    main()
