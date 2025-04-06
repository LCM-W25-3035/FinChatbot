import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os
import bcrypt
import re

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # Replace with your region
USER_TABLE = os.getenv("USER_TABLE")
user_table = dynamodb.Table(USER_TABLE)

# Authenticate user
def authenticate_user(email, password):
    try:
        response = user_table.scan(
            FilterExpression="u_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        items = response.get("Items", [])

        if not items:
            return {"error": "Invalid email or password!"}

        for item in items:
            # Check if the user is approved
            if not item.get("is_approved", False):
                return {"error": "Your account is not approved. Please contact the administrator."}

            stored_password = item.get("u_pwd", "")

            # Check if stored password is hashed
            if stored_password.startswith("$2b$"):
                # If hashed, verify using bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return {"message": "Login successful!", "u_id": item["u_id"]}
            else:
                # If not hashed, do a direct comparison
                if password == stored_password:
                    return {"message": "Login successful!", "u_id": item["u_id"]}

        return {"error": "Invalid email or password!"}
    except ClientError as e:
        return {"error": str(e)}

def main():
    st.title("User Login")

    # Email validation
    def is_valid_email(email):
        """Check if the input string is a valid email address."""
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(email_regex, email)

    email = st.text_input("Enter your email:")

    if email:
        if is_valid_email(email):
            st.success("Valid email address!")
        else:
            st.error("Invalid email address. Please enter a valid email.")

    password = st.text_input("Enter your password", type="password")

    if st.button("Don't have an account? Register here."):
        st.switch_page("pages/user_register.py")

    if st.button("Login"):
        if not email or not password:
            st.error("Please fill all fields!")
        else:
            response = authenticate_user(email, password)
            if "error" in response:
                st.error(f"Login failed: {response['error']}")
            else:
                st.success("Login successful! Redirecting to FinChatbot...")
                st.session_state["u_id"] = response["u_id"]
                st.switch_page("app.py")

if __name__ == "__main__":
    main()
