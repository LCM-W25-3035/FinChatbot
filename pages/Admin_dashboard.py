import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
USER_TABLE = os.getenv("USER_TABLE")
user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    """Fetch all users from DynamoDB."""
    try:
        response = user_table.scan()
        return response.get("Items", [])
    except ClientError as e:
        return {"error": str(e)}

def update_user_approval(user_id, approval_status):
    """Update user approval status in DynamoDB."""
    try:
        response = user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET is_approved = :status",
            ExpressionAttributeValues={":status": approval_status},
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes", None)
    except ClientError as e:
        st.error(f"Error updating approval status: {e}")
        return None

def edit_user_info(user_id, new_email, new_name, new_address):
    """Edit user details in DynamoDB."""
    try:
        response = user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET u_email = :email, u_name = :name, u_address = :address",
            ExpressionAttributeValues={
                ":email": new_email, ":name": new_name, ":address": new_address
            },
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes", None)
    except ClientError as e:
        st.error(f"Error updating user information: {e}")
        return None

def delete_user(user_id):
    """Delete a user from DynamoDB."""
    try:
        response = user_table.delete_item(Key={"u_id": user_id})
        return response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200
    except ClientError as e:
        st.error(f"Error deleting user: {e}")
        return False

def check_admin():
    """Check if user is an admin."""
    if "is_admin" not in st.session_state or not st.session_state["is_admin"]:
        st.error("Unauthorized access! Please log in as an admin.")
        return False
    return True

def show_user_details(user):
    """Display user details."""
    st.write(f"User ID: {user.get('u_id', 'N/A')}")
    st.write(f"User Email: {user.get('u_email', 'N/A')}")
    st.write(f"User Name: {user.get('u_name', 'N/A')}")
    st.write(f"User Address: {user.get('u_address', 'N/A')}")

def handle_approval_status(user):
    """Handle user approval actions."""
    user_id = user.get('u_id', 'N/A')
    user_email = user.get('u_email', 'N/A')
    approval_status = st.radio(
        f"Approval Status for {user_email}",
        options=["Approved", "Not Approved"],
        index=0 if user.get("is_approved", False) else 1,
        key=f"approval_{user_id}"
    )
    
    if approval_status == "Approved" and not user.get("is_approved", False):
        if st.button(f"Approve {user_email}", key=f"approve_{user_id}"):
            if update_user_approval(user_id, True):
                st.rerun()
    elif approval_status == "Not Approved" and user.get("is_approved", False):
        if st.button(f"Disapprove {user_email}", key=f"disapprove_{user_id}"):
            if update_user_approval(user_id, False):
                st.rerun()

def handle_user_actions(user):
    """Handle edit and delete actions for a user."""
    user_id = user.get('u_id', 'N/A')
    user_email = user.get('u_email', 'N/A')
    
    if st.button(f"Edit {user_email}", key=f"edit_{user_id}"):
        edit_user_form(user)
    
    if st.button(f"Delete {user_email}", key=f"delete_{user_id}"):
        if delete_user(user_id):
            st.rerun()

def display_user_info(user):
    """Display user details and associated actions."""
    with st.expander(f"User: {user.get('u_email', 'N/A')}"):
        show_user_details(user)
        handle_approval_status(user)
        handle_user_actions(user)

def edit_user_form(user):
    """Render form for editing user details."""
    user_id = user.get('u_id', 'N/A')
    new_email = st.text_input("New Email", value=user.get('u_email', ''))
    new_name = st.text_input("New Name", value=user.get('u_name', ''))
    new_address = st.text_input("New Address", value=user.get('u_address', ''))

    if st.button("Save Changes"):
        if edit_user_info(user_id, new_email, new_name, new_address):
            st.success("User information updated.")
            st.rerun()

def main():
    """Admin Dashboard UI."""
    st.title("Admin Dashboard")
    
    if not check_admin():
        return
    
    users = fetch_users()
    
    if "error" in users:
        st.error(f"Error fetching users: {users['error']}")
        return
    
    for user in users:
        display_user_info(user)
    
    if st.button("Logout"):
        st.session_state["is_admin"] = False
        st.switch_page("Admin_login")

if __name__ == "__main__":
    main()
