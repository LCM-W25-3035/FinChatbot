import streamlit as st
import boto3
import uuid
from botocore.exceptions import ClientError
import os
import re
import bcrypt

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
USER_TABLE = os.getenv("USER_TABLE")
user_table = dynamodb.Table(USER_TABLE)


def encrypt_password(password):
    """Encrypt the password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def insert_user(u_id, email, password):
    """Insert a new user into DynamoDB."""
    password = encrypt_password(password)
    try:
        user_table.put_item(Item={"u_id": u_id, "u_email": email, "u_pwd": password})
        return {"message": "User inserted successfully!"}
    except ClientError as e:
        return {"error": str(e)}


def register_user(email, password):
    """Register a new user if the email is not already taken."""
    try:
        response = user_table.scan(
            FilterExpression="u_email = :email", ExpressionAttributeValues={":email": email}
        )
        if response.get("Items"):
            return {"error": "Email is already registered!"}

        u_id = str(uuid.uuid4())
        insert_response = insert_user(u_id, email, password)
        if "error" in insert_response:
            return {"error": insert_response["error"]}

        return {"message": "User registered successfully!", "u_id": u_id}
    except ClientError as e:
        return {"error": str(e)}


def validate_password(password):
    """Check if the password meets security requirements."""
    regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(regex, password))


def is_valid_email(email):
    """Check if the input string is a valid email address."""
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_regex, email))


def handle_email_input():
    """Handle email validation input."""
    email = st.text_input("Enter your email:")
    if email and not is_valid_email(email):
        st.error("Invalid email address. Please enter a valid email.")
    return email


def handle_password_input():
    """Handle password validation input."""
    password = st.text_input("Enter your password", type="password")
    confirm_password = st.text_input("Confirm your password", type="password")

    if password and confirm_password and password != confirm_password:
        st.error("Passwords do not match!")

    if password and not validate_password(password):
        st.error(
            "Password must contain:\n"
            "- At least 8 characters\n"
            "- At least 1 uppercase letter\n"
            "- At least 1 lowercase letter\n"
            "- At least 1 special character (@, $, etc.)\n"
            "- At least 1 number"
        )

    return password, confirm_password


def register_button_action(email, password, confirm_password):
    """Handle user registration."""
    if not email or not password:
        st.error("Please fill all fields!")
        return

    if password != confirm_password:
        return

    response = register_user(email, password)
    if "error" in response:
        st.error(f"Registration failed: {response['error']}")
    else:
        st.success("Registration successful! Redirecting to login page...")
        st.session_state["u_id"] = response["u_id"]
        st.switch_page("pages/user_login.py")


def main():
    """Main function for the user registration page."""
    st.title("User Registration")

    email = handle_email_input()
    password, confirm_password = handle_password_input()

    if st.button("Already have an account? Login here."):
        st.switch_page("pages/user_login.py")

    if st.button("Register"):
        register_button_action(email, password, confirm_password)


if __name__ == "__main__":
    main()
