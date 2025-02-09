import streamlit as st
import boto3
import uuid
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import os
import re
import bcrypt

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # Replace with your region
USER_TABLE = os.getenv("USER_TABLE")
user_table = dynamodb.Table(USER_TABLE)


# Encrypt the password
def encrypt_password(password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

# Insert user into tbl_user table
def insert_user(u_id, email, password):
    password = encrypt_password(password)
    try:
        user_table.put_item(
            Item={
                "u_id": u_id,
                "u_email": email,
                "u_pwd": password
            }
        )
        return {"message": "User inserted successfully!"}
    except ClientError as e:
        return {"error": str(e)}

# Register a new user
def register_user(email, password):
    # Check if email already exists
    try:
        response = user_table.scan(
            FilterExpression="u_email = :email",
            ExpressionAttributeValues={":email": email}
        )
        if response.get("Items"):
            return {"error": "Email is already registered!"}
        
        # Create new user
        u_id = str(uuid.uuid4())  # Generate a unique user ID
        insert_response = insert_user(u_id, email, password)
        if "error" in insert_response:
            return {"error": insert_response["error"]}
        
        return {"message": "User registered successfully!", "u_id": u_id}
    except ClientError as e:
        return {"error": str(e)}

# Validate password
def validate_password(password):
    # Regex for password validation
    regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if not re.match(regex, password):
        return False
    return True

def main():
    st.title("User Registration")
    
    # Registration form
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
    confirm_password = st.text_input("Confirm your password", type="password")
    
    if st.button("Already have an account? Login here."):
        st.switch_page("pages/user_login.py")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match!")
        elif not email or not password:
            st.error("Please fill all fields!")
        elif not validate_password(password):
            st.error(
                "Password must contain:\n"
                "- At least 8 characters\n"
                "- At least 1 uppercase letter\n"
                "- At least 1 lowercase letter\n"
                "- At least 1 special character (@, $, etc.)\n"
                "- At least 1 number"
            )
        else:
            response = register_user(email, password)
            if "error" in response:
                st.error(f"Registration failed: {response['error']}")
            else:
                st.success("Registration successful! Redirecting to login page...")
                st.session_state["u_id"] = response["u_id"]
                st.switch_page("pages/user_login.py")

if __name__ == "__main__":
    main()