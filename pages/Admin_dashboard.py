import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # Update with your AWS region
USER_TABLE = os.getenv("USER_TABLE")  # Ensure your user table environment variable is set
user_table = dynamodb.Table(USER_TABLE)

# Fetch all users from DynamoDB
def fetch_users():
    try:
        response = user_table.scan()
        return response.get("Items", [])
    except ClientError as e:
        return {"error": str(e)}

# Update user approval status
def update_user_approval(user_id, approval_status):
    try:
        # Update the user's approval status in DynamoDB
        response = user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET is_approved = :status",
            ExpressionAttributeValues={":status": approval_status},
            ReturnValues="ALL_NEW"  # Ensure that we get the updated item in the response
        )
        
        updated_item = response.get("Attributes", None)
        if updated_item:
            st.write(f"User {updated_item['u_email']} has been {'approved' if approval_status else 'not approved'} successfully.")
        else:
            st.warning(f"No user found with ID {user_id}. Update failed.")
        
        return True
    except ClientError as e:
        st.error(f"Error updating approval status: {e}")
        return False

# Edit user information
def edit_user_info(user_id, new_email, new_name, new_address):
    try:
        response = user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET u_email = :email, u_name = :name, u_address = :address",
            ExpressionAttributeValues={
                ":email": new_email,
                ":name": new_name,
                ":address": new_address
            },
            ReturnValues="ALL_NEW"
        )
        
        updated_item = response.get("Attributes", None)
        if updated_item:
            st.success(f"User {updated_item['u_email']} information has been updated.")
            return True
        else:
            st.warning(f"No user found with ID {user_id}. Edit failed.")
            return False
    except ClientError as e:
        st.error(f"Error updating user information: {e}")
        return False

# Delete user
def delete_user(user_id):
    try:
        # Delete the user from DynamoDB
        response = user_table.delete_item(
            Key={"u_id": user_id}
        )
        
        # Check if the deletion was successful
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200:
            st.success(f"User with ID {user_id} has been deleted successfully.")
            return True
        else:
            st.warning(f"Failed to delete user with ID {user_id}.")
            return False
    except ClientError as e:
        st.error(f"Error deleting user: {e}")
        return False

# Admin Dashboard UI
def main():
    st.title("Admin Dashboard")

    # Check if the user is an admin
    if "is_admin" not in st.session_state or not st.session_state["is_admin"]:
        st.error("Unauthorized access! Please log in as an admin.")
        return

    # Fetch user data from DynamoDB
    users = fetch_users()

    if "error" in users:
        st.error(f"Error fetching users: {users['error']}")
    else:
        # Display all users for the admin to approve or not approve
        for user in users:
            user_id = user.get('u_id', 'N/A')
            user_email = user.get('u_email', 'N/A')
            user_name = user.get('u_name', 'N/A')  # Assuming the user has a 'u_name' field
            user_address = user.get('u_address', 'N/A')  # Assuming the user has a 'u_address' field

            with st.expander(f"User: {user_email}"):
                # Display user information
                st.write(f"User ID: {user_id}")
                st.write(f"User Email: {user_email}")
                st.write(f"User Name: {user_name}")
                st.write(f"User Address: {user_address}")

                # Radio button for "Approved or Not Approved"
                approval_status = st.radio(
                    f"Approval Status for {user_email}",
                    options=["Approved", "Not Approved"],
                    index=0 if user.get("is_approved", False) else 1,
                    key=f"approval_{user_id}"
                )

                # Save approval status button for approval
                if approval_status == "Approved" and not user.get("is_approved", False):
                    if st.button(f"Approve {user_email}", key=f"approve_{user_id}"):
                        if update_user_approval(user_id, True):
                            st.success(f"User {user_email} has been approved.")
                            st.session_state['approved_user_id'] = user_id  # Store approved user id to edit or delete
                            st.rerun()

                # Save approval status button for disapproval
                elif approval_status == "Not Approved" and user.get("is_approved", False):
                    if st.button(f"Disapprove {user_email}", key=f"disapprove_{user_id}"):
                        if update_user_approval(user_id, False):
                            st.success(f"User {user_email} has been disapproved.")
                            st.session_state['approved_user_id'] = None  # Reset approved user id
                            st.rerun()

                # Only show Edit and Delete options after approval or disapproval
                if 'approved_user_id' in st.session_state and st.session_state['approved_user_id'] == user_id:
                    st.subheader(f"Actions for {user_email}:")
                    action = st.radio(
                        f"Choose action for {user_email}",
                        options=["Edit User", "Delete User"],
                        key=f"action_{user_id}"
                    )
                    
                    if action == "Edit User":
                        # Allow admin to edit user details
                        new_email = st.text_input(f"New Email for {user_email}", value=user_email)
                        new_name = st.text_input(f"New Name for {user_name}", value=user_name)
                        new_address = st.text_input(f"New Address for {user_address}", value=user_address)
                        
                        # Save changes button for editing user info
                        if st.button(f"Save Changes for {user_email}", key=f"save_{user_id}"):
                            if edit_user_info(user_id, new_email, new_name, new_address):
                                st.rerun()

                    elif action == "Delete User":
                        # Confirm delete action
                        if st.button(f"Delete User {user_email}", key=f"delete_{user_id}"):
                            if delete_user(user_id):
                                st.rerun()

    # Logout button for admin
    if st.button("Logout"):
        st.session_state["is_admin"] = False
        st.switch_page("Admin_login")  # Redirect back to login page

if __name__ == "__main__":
    main()
