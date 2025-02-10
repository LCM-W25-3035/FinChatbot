import streamlit as st
import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# AWS DynamoDB Configuration
dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

USER_TABLE = os.getenv("USER_TABLE")
user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    """Fetch all users from DynamoDB."""
    try:
        response = user_table.scan()
        users = response.get("Items", [])
        return users
    except ClientError as e:
        st.error(f"Error fetching users: {str(e)}")
        return []

def update_user_approval(user_id, user_email, approval_status):
    """Update user approval status in DynamoDB."""
    try:
        response = user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET is_approved = :val",
            ExpressionAttributeValues={":val": approval_status},
            ReturnValues="ALL_NEW"
        )
        st.success(f"User {user_id} {'approved' if approval_status else 'disapproved'} successfully!")
        st.rerun()
    except ClientError as e:
        st.error(f"Error updating user: {str(e)}")

def update_user_data(user_id, user_email, new_password, approval_status):
    """Update user data in DynamoDB."""
    try:
        update_expression = []
        expression_values = {}
        
        if new_password:
            update_expression.append("u_pwd = :new_pwd")
            expression_values[":new_pwd"] = new_password
        
        update_expression.append("is_approved = :approval")
        expression_values[":approval"] = approval_status
        
        if update_expression:
            response = user_table.update_item(
                Key={"u_id": user_id, "u_email": user_email},
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW"
            )
            st.success(f"User {user_id} updated successfully!")
            st.rerun()
    except ClientError as e:
        st.error(f"Error updating user data: {str(e)}")

def main():
    st.title("Admin Panel - User Management")
    
    users = fetch_users()
    if not users:
        st.warning("No users found.")
        return
    
    df = pd.DataFrame(users)
    st.dataframe(df)
    
    for user in users:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button(f"Approve {user.get('u_id')}", key=f"approve_{user.get('u_id')}"):
                update_user_approval(user.get("u_id"), user.get("u_email"), True)
        with col2:
            if st.button(f"Disapprove {user.get('u_id')}", key=f"disapprove_{user.get('u_id')}"):
                update_user_approval(user.get("u_id"), user.get("u_email"), False)
        with col3:
            if st.button("Edit", key=f"edit_{user.get('u_id')}"):
                with st.expander(f"Edit User: {user.get('u_email')}"):
                    new_password = st.text_input("Password", user.get("u_pwd"), type="password")
                    new_approval = st.checkbox("Approved", value=user.get("is_approved", False))
                    if st.button("Save Changes", key=f"save_{user.get('u_id')}"):
                        update_user_data(user.get("u_id"), user.get("u_email"), new_password, new_approval)

if __name__ == "__main__":
    main()
