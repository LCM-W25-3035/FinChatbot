import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # Update with your AWS region
ADMIN_TABLE = os.getenv("ADMIN_TABLE")
admin_table = dynamodb.Table(ADMIN_TABLE)

# Authenticate Admin
def authenticate_admin(email, password):
    try:
        response = admin_table.scan(
            FilterExpression="a_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        items = response.get("Items", [])

        if not items:
            return False  # Invalid credentials

        for item in items:
            stored_password = item.get("a_password", "")

            if password == stored_password:
                return True  # Successful login

        return False  # Invalid credentials
    except ClientError as e:
        st.error(f"Error: {e}")
        return False

# Main login function
def main():
    st.title("Admin Login")

    email = st.text_input("Enter your email:")
    password = st.text_input("Enter your password", type="password")

    if st.button("Login"):
        if authenticate_admin(email, password):
            st.success("Login successful! Redirecting...")
            st.session_state["is_admin"] = True  # Set session state
            st.switch_page("pages/Admin_dashboard.py")  # Redirect to admin dashboard
        else:
            st.error("Invalid email or password!")

if __name__ == "__main__":
    main()
