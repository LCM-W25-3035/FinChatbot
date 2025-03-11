import streamlit as st
import boto3
import os
from botocore.exceptions import ClientError

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

USER_TABLE = os.getenv("USER_TABLE")

user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    """Fetch all users from DynamoDB."""
    try:
        response = user_table.scan()
        return response.get("Items", [])
    except ClientError as e:
        st.error(f"Error fetching users: {e}")
        return []

# Fetch user details
def fetch_user(user_id):
    try:
        response = user_table.get_item(Key={"u_id": user_id})
        return response.get("Item", {})
    except ClientError as e:
        st.error(f"Error fetching user: {e}")
        return {}

# Update user status (Approve/Disapprove)
def update_user_status(user_id, status):
    try:
        user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET approved = :status",
            ExpressionAttributeValues={":status": status}
        )
        st.success(f"User status updated to {status}.")
        st.rerun()
    except ClientError as e:
        st.error(f"Error updating status: {e}")

def edit_user_info(user_id, new_email, new_name, new_address):
    """Edit user details in DynamoDB."""
    try:
        user_table.update_item(
            Key={"u_id": user_id},
            UpdateExpression="SET u_email = :email, u_name = :name, u_address = :address",
            ExpressionAttributeValues={
                ":email": new_email,
                ":name": new_name,
                ":address": new_address
            }
        )
        st.success("User information updated successfully.")
    except ClientError as e:
        st.error(f"Error updating user: {e}")

# Edit PDF metadata
def edit_pdf_info(user_id, pdf_id, new_title, new_description):
    try:
        user = fetch_user(user_id)
        if "pdfs" in user:
            for pdf in user["pdfs"]:
                if pdf["pdf_id"] == pdf_id:
                    pdf["pdf_title"] = new_title
                    pdf["pdf_description"] = new_description
                    break
            user_table.update_item(
                Key={"u_id": user_id},
                UpdateExpression="SET pdfs = :pdfs",
                ExpressionAttributeValues={":pdfs": user["pdfs"]}
            )
            st.success(f"PDF {pdf_id} updated successfully.")
    except ClientError as e:
        st.error(f"Error updating PDF: {e}")

# Delete PDF from DynamoDB
def delete_pdf(user_id, pdf_id):
    try:
        user = fetch_user(user_id)
        if "pdfs" in user:
            updated_pdfs = [pdf for pdf in user["pdfs"] if pdf["pdf_id"] != pdf_id]
            user_table.update_item(
                Key={"u_id": user_id},
                UpdateExpression="SET pdfs = :pdfs",
                ExpressionAttributeValues={":pdfs": updated_pdfs}
            )
            st.success(f"PDF {pdf_id} deleted successfully.")
            st.experimental_rerun()
    except ClientError as e:
        st.error(f"Error deleting PDF: {e}")

# Delete only PDF information from DynamoDB
def delete_user_pdfs(user_id):
    try:
        user = fetch_user(user_id)
        if "pdfs" in user and user["pdfs"]:
            user_table.update_item(
                Key={"u_id": user_id},
                UpdateExpression="REMOVE pdfs"
            )
            st.success(f"PDFs for user {user_id} deleted successfully.")
            st.rerun()
        else:
            st.info("No PDFs available to delete.")
    except ClientError as e:
        st.error(f"Error deleting PDFs: {e}")

# Main Admin Dashboard
def main():
    st.title("Admin Dashboard")

    # Ensure admin access
    if "is_admin" not in st.session_state or not st.session_state["is_admin"]:
        st.error("Unauthorized access! Admins only.")
        st.stop()

    users = fetch_users()

    # Display each user with actions
    for user in users:
        user_id = user.get('u_id', 'N/A')
        user_email = user.get('u_email', 'N/A')
        user_name = user.get('u_name', 'N/A')
        user_address = user.get('u_address', 'N/A')
        approved_status = user.get('approved', 'Pending')

        with st.expander(f"User: {user_email}"):
            st.write(f"User ID: {user_id}")
            st.write(f"Name: {user_name}")
            st.write(f"Address: {user_address}")
            st.write(f"Status: {approved_status}")

            # Approve or Disapprove users
            if approved_status == 'Pending':
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Approve {user_email}", key=f"approve_{user_id}"):
                        update_user_status(user_id, "Approved")
                with col2:
                    if st.button(f"Disapprove {user_email}", key=f"disapprove_{user_id}"):
                        update_user_status(user_id, "Disapproved")

            if approved_status == 'Approved':
                action = st.radio("Select Action", ("Edit", "Delete"), key=f"action_{user_id}")

                if action == "Edit":
                    edit_user_section(user_id)

                elif action == "Delete":
                    delete_user_pdfs(user_id)

    # Logout button
    if st.button("Logout"):
        st.session_state["is_admin"] = False
        st.rerun()

# Edit user and PDFs section
def edit_user_section(user_id):
    st.subheader("Edit User & PDF Information")

    user = fetch_user(user_id)
    if not user:
        st.error("User not found.")
        return

    new_email = st.text_input("Email", value=user.get("u_email", ""), key=f"email_{user_id}")
    new_name = st.text_input("Name", value=user.get("u_name", ""), key=f"name_{user_id}")
    new_address = st.text_input("Address", value=user.get("u_address", ""), key=f"address_{user_id}")

    if st.button("Update User Information", key=f"update_user_{user_id}"):
        edit_user_info(user_id, new_email, new_name, new_address)

    # Edit PDFs
    if "pdfs" in user:
        st.subheader("Edit PDFs")
        for pdf in user["pdfs"]:
            pdf_id = pdf.get("pdf_id")
            pdf_title = st.text_input(f"Title for {pdf_id}", value=pdf.get("pdf_title", ""), key=f"title_{pdf_id}")
            pdf_description = st.text_area(f"Description for {pdf_id}", value=pdf.get("pdf_description", ""), key=f"desc_{pdf_id}")

            if st.button(f"Update PDF {pdf_id}", key=f"update_pdf_{pdf_id}"):
                edit_pdf_info(user_id, pdf_id, pdf_title, pdf_description)

if __name__ == "__main__":
    main()
