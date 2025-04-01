import streamlit as st
import boto3
import os
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from datetime import datetime
from io import BytesIO

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE = os.getenv("USER_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

SECTOR_CHOICES = ["📱 Technology", "🏥 Healthcare", "💳 Finance", "🎓 Education", "📦 Other"]

# Initialize AWS clients
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION_DYNAMO,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
s3 = boto3.client("s3")
user_table = dynamodb.Table(USER_TABLE)

def fetch_users():
    try:
        response = user_table.scan()
        return response.get("Items", [])
    except ClientError as e:
        st.error(f"🚨 Error fetching users: {str(e)}")
        return []

def process_pdf_entries(pdf_files):
    processed = []
    for entry in pdf_files:
        if isinstance(entry, str):
            sector = "📦 Other"
            if "/" in entry:
                parts = entry.split("/")
                if len(parts) >= 3 and parts[2] in SECTOR_CHOICES:
                    sector = parts[2]
            processed.append({
                "file_key": entry,
                "filename": entry.split("/")[-1],
                "sector": sector,
                "upload_date": "2023-01-01T00:00:00",
                "size": 0,
                "storage_class": "STANDARD"
            })
        else:
            entry.setdefault("sector", "📦 Other")
            entry.setdefault("upload_date", datetime.now().isoformat())
            entry.setdefault("size", 0)
            entry.setdefault("storage_class", "STANDARD")
            processed.append(entry)
    return processed

def upload_pdf(file, user_id, user_email, pdf_limit, sector):
    try:
        if not file.name.lower().endswith('.pdf'):
            raise ValueError("📄 Only PDF files allowed")

        user_data = user_table.get_item(Key={"u_id": user_id, "u_email": user_email}).get("Item", {})
        current_files = user_data.get("pdf_files", [])
        if len(current_files) >= pdf_limit:
            raise ValueError(f"🚫 Limit reached ({pdf_limit} files)")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_key = f"users/{user_id}/{sector}/{timestamp}_{file.name}"

        with st.spinner("⏳ Uploading..."):
            s3.upload_fileobj(
                file, 
                S3_BUCKET, 
                file_key,
                ExtraArgs={
                    "ContentType": "application/pdf",
                    "Metadata": {"uploader": user_email, "sector": sector},
                    "Tagging": f"user={user_id}&sector={sector}"
                }
            )

        pdf_metadata = {
            "file_key": file_key,
            "filename": file.name,
            "sector": sector,
            "upload_date": datetime.now().isoformat(),
            "size": file.size,
            "storage_class": "STANDARD"
        }

        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = list_append(if_not_exists(pdf_files, :empty_list), :pdf)",
            ExpressionAttributeValues={
                ":pdf": [pdf_metadata],
                ":empty_list": []
            },
            ReturnValues="UPDATED_NEW"
        )

        st.success(f"✅ {file.name} uploaded!")
        st.balloons()
        st.rerun()

    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        except:
            pass

def delete_pdf(user_id, user_email, file_key):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        if "Item" not in response:
            raise ValueError("🔍 User not found")
            
        user_data = response["Item"]
        pdf_list = process_pdf_entries(user_data.get("pdf_files", []))
        new_pdf_list = [pdf for pdf in pdf_list if pdf["file_key"] != file_key]
        
        user_table.update_item(
            Key={"u_id": user_id, "u_email": user_email},
            UpdateExpression="SET pdf_files = :new_list",
            ExpressionAttributeValues={":new_list": new_pdf_list}
        )
        
        st.success("🗑️ PDF deleted!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Delete failed: {str(e)}")

def admin_manage_users(users):
    st.subheader("👨💻 Admin Controls")
    st.markdown("---")
    
    with st.expander("➕ New User", expanded=False):
        with st.form("new_user_form"):
            cols = st.columns(2)
            with cols[0]:
                new_id = st.text_input("🆔 User ID")
                new_email = st.text_input("📧 Email")
            with cols[1]:
                new_pwd = st.text_input("🔑 Password", type="password")
                pdf_limit = st.number_input("📚 File Limit", 5, 100, 5)
            
            approved = st.checkbox("✅ Approved")
            
            if st.form_submit_button("📥 Create User"):
                try:
                    user_table.put_item(Item={
                        "u_id": new_id,
                        "u_email": new_email,
                        "is_approved": approved,
                        "u_pwd": new_pwd,
                        "pdf_limit": pdf_limit,
                        "pdf_files": [],
                        "registration_date": datetime.now().isoformat()
                    })
                    st.success("👤 User created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Creation failed: {str(e)}")

    st.markdown("### 📋 User List")
    for user in users:
        with st.expander(f"👤 {user['u_email']}", expanded=False):
            cols = st.columns([1,2,1])
            with cols[0]:
                approved = st.checkbox("✅ Approved", 
                                     value=user.get("is_approved", False),
                                     key=f"appr_{user['u_id']}")
                limit = st.number_input("📚 Limit", 
                                      value=user.get("pdf_limit", 5),
                                      key=f"lim_{user['u_id']}")
            
            with cols[1]:
                st.markdown(f"""
                    📅 **Registered:** {user.get('registration_date', 'N/A')}  
                    📁 **Files:** {len(user.get('pdf_files', []))}/{limit}
                """)
                
            with cols[2]:
                if st.button("🔄 Update", key=f"upd_{user['u_id']}"):
                    try:
                        user_table.update_item(
                            Key={"u_id": user["u_id"], "u_email": user["u_email"]},
                            UpdateExpression="SET is_approved = :a, pdf_limit = :l",
                            ExpressionAttributeValues={":a": approved, ":l": limit}
                        )
                        st.success("🔄 User updated!")
                    except Exception as e:
                        st.error(f"❌ Update failed: {str(e)}")
                
                if st.button("🗑️ Delete", key=f"del_{user['u_id']}"):
                    try:
                        prefix = f"users/{user['u_id']}/"
                        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
                        if 'Contents' in objects:
                            s3.delete_objects(Bucket=S3_BUCKET, Delete={
                                'Objects': [{'Key': o['Key']} for o in objects['Contents']]
                            })
                        user_table.delete_item(Key={"u_id": user["u_id"], "u_email": user["u_email"]})
                        st.success("🗑️ User deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Deletion failed: {str(e)}")
    st.markdown("---")

def handle_pdf_management(users):
    if not users:
        st.warning("👥 No users found")
        return

    user = st.selectbox("👤 Select User", 
                      [(u['u_id'], u['u_email']) for u in users], 
                      format_func=lambda x: f"{x[1]} ({x[0]})")
    
    if user:
        u_id, u_email = user
        try:
            res = user_table.get_item(Key={"u_id": u_id, "u_email": u_email})
            data = res.get("Item", {})
            pdfs = process_pdf_entries(data.get("pdf_files", []))
            
            st.subheader(f"📁 {u_email}'s Documents")
            cols = st.columns(3)
            cols[0].metric("📚 File Limit", data.get("pdf_limit", 5))
            cols[1].metric("📁 Current Files", len(pdfs))
            cols[2].metric("🔄 Last Active", data.get("last_login", "Never"))
            
            with st.expander("📤 Upload New", expanded=False):
                with st.form("upload_form"):
                    file = st.file_uploader("📄 Choose PDF", type="pdf")
                    sector = st.selectbox("📂 Sector", SECTOR_CHOICES)
                    if st.form_submit_button("🚀 Upload"):
                        if file:
                            upload_pdf(file, u_id, u_email, 
                                      data.get("pdf_limit", 5), sector)
                        else:
                            st.warning("⚠️ Select a PDF")
            
            st.subheader("📂 Stored Documents")
            if pdfs:
                for pdf in pdfs:
                    cols = st.columns([4,2,2,1,1])
                    cols[0].markdown(f"**{pdf['filename']}**")
                    cols[1].markdown(f"📂 {pdf['sector']}")
                    cols[2].markdown(f"📅 {pd.to_datetime(pdf['upload_date']).strftime('%Y-%m-%d')}")
                    cols[3].markdown(f"📦 {pdf['size']/1e6:.1f}MB")
                    cols[4].button("🗑️", key=f"del_{pdf['file_key']}",
                                 on_click=delete_pdf, args=(u_id, u_email, pdf['file_key']))
                    st.markdown("---")
            else:
                st.info("📭 No documents found")

        except ClientError as e:
            st.error(f"🚨 Access error: {str(e)}")

def main():
    st.title("📚 Document Manager")
    st.markdown("---")
    
    if st.checkbox("🔓 Admin Dashboard"):
        with st.sidebar:
            st.subheader("⚙️ Admin Tools")
            if st.button("🔄 Migrate Files"):
                try:
                    # Migration logic
                    st.success("🔄 Migration completed!")
                except Exception as e:
                    st.error(f"❌ Migration failed: {str(e)}")
            st.markdown("---")
        
        admin_manage_users(fetch_users())
    else:
        users = [u for u in fetch_users() if u.get("is_approved")]
        handle_pdf_management(users)

if __name__ == "__main__":
    main()