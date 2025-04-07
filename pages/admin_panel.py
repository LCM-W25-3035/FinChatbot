import streamlit as st
import boto3
import os
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from datetime import datetime
from decimal import Decimal

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION_DYNAMO = os.getenv("AWS_REGION_DYNAMO")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
USER_TABLE = os.getenv("USER_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

# Sector Configuration
SECTOR_CONFIG = {
    "technology": "📱 Technology",
    "healthcare": "🏥 Healthcare",
    "finance": "💳 Finance",
    "education": "🎓 Education",
    "other": "📦 Other"
}

def get_display_sector(clean_sector):
    return SECTOR_CONFIG.get(clean_sector.lower(), SECTOR_CONFIG["other"])

def get_clean_sector(display_sector):
    for key, value in SECTOR_CONFIG.items():
        if value == display_sector:
            return key
    return "other"

# Initialize AWS clients
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION_DYNAMO,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
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
        processed_entry = {
            "file_key": "",
            "filename": "Unknown File",
            "sector": SECTOR_CONFIG["other"],
            "upload_date": datetime.now().isoformat(),
            "size": Decimal(0),
            "storage_class": "STANDARD"
        }

        if isinstance(entry, dict):
            filename = entry.get("filename") or entry.get("file_key", "").split("/")[-1]
            clean_sector = entry.get("sector", "other")
            processed_entry.update({
                "file_key": entry.get("file_key", ""),
                "filename": filename,
                "sector": get_display_sector(clean_sector),
                "size": entry.get("size", Decimal(0)),
                "upload_date": entry.get("upload_date", datetime.now().isoformat())
            })

        elif isinstance(entry, str):
            parts = entry.split('/')
            folder = parts[0].lower()
            processed_entry.update({
                "file_key": entry,
                "filename": entry.split("/")[-1],
                "sector": get_display_sector(folder)
            })

        processed.append(processed_entry)
    return processed

def upload_pdf(file, user_id, user_email, pdf_limit, display_sector):
    try:
        clean_sector = get_clean_sector(display_sector)
        
        if not file.name.lower().endswith('.pdf'):
            raise ValueError("📄 Only PDF files allowed")

        user_data = user_table.get_item(Key={"u_id": user_id, "u_email": user_email}).get("Item", {})
        current_files = user_data.get("pdf_files", [])
        user_limit = int(user_data.get("pdf_limit", Decimal(5)))
        
        if len(current_files) >= user_limit:
            raise ValueError(f"🚫 Limit reached ({user_limit} files)")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_key = f"{clean_sector}/{user_id}/{timestamp}_{file.name}"

        with st.spinner("⏳ Uploading..."):
            s3.upload_fileobj(
                file, 
                S3_BUCKET, 
                file_key,
                ExtraArgs={
                    "ContentType": "application/pdf",
                    "Metadata": {"uploader": user_email, "sector": clean_sector},
                    "Tagging": f"user={user_id}&sector={clean_sector}"
                }
            )

        pdf_metadata = {
            "file_key": file_key,
            "filename": file.name,
            "sector": clean_sector,
            "upload_date": datetime.now().isoformat(),
            "size": Decimal(str(file.size)),
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

        st.success(f"✅ {file.name} uploaded to {display_sector}!")
        st.balloons()
        st.rerun()

    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        except Exception:
            pass

def delete_pdf(user_id, user_email, file_key):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=file_key)
        
        response = user_table.get_item(Key={"u_id": user_id, "u_email": user_email})
        user_data = response.get("Item", {})
        pdf_list = user_data.get("pdf_files", [])
        new_pdf_list = [pdf for pdf in pdf_list if pdf.get("file_key", "") != file_key]
        
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

    show_new_user_form()
    st.markdown("### 📋 User List")
    for user in users:
        render_user_card(user)
    st.markdown("---")

def show_new_user_form():
    with st.expander("➕ New User", expanded=False):
        with st.form("new_user_form"):
            cols = st.columns(2)
            new_id = cols[0].text_input("🆔 User ID")
            new_email = cols[0].text_input("📧 Email")
            new_pwd = cols[1].text_input("🔑 Password", type="password")
            pdf_limit = cols[1].number_input("📚 File Limit", 5, 100, 5)
            approved = st.checkbox("✅ Approved")

            if st.form_submit_button("📥 Create User"):
                create_user(new_id, new_email, new_pwd, approved, pdf_limit)

def create_user(new_id, new_email, new_pwd, approved, pdf_limit):
    try:
        user_table.put_item(Item={
            "u_id": new_id,
            "u_email": new_email,
            "u_pwd": new_pwd,
            "is_approved": approved,
            "pdf_limit": int(pdf_limit),
            "pdf_files": [],
            "registration_date": datetime.now().isoformat()
        })
        st.success("👤 User created!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Creation failed: {str(e)}")

def render_user_card(user):
    unique_key = f"{user['u_id']}_{user['u_email']}"
    with st.expander(f"👤 {user['u_email']}", expanded=False):
        cols = st.columns([1, 2, 1])

        approved = cols[0].checkbox("✅ Approved", 
                                   value=user.get("is_approved", False),
                                   key=f"appr_{unique_key}")
        current_limit = int(user.get("pdf_limit", Decimal(5)))
        limit = cols[0].number_input("📚 Limit", value=current_limit, key=f"lim_{unique_key}")

        cols[1].markdown(f"""
            📅 **Registered:** {user.get('registration_date', 'N/A')}  
            📁 **Files:** {len(user.get('pdf_files', []))}/{current_limit}
        """)

        if cols[2].button("🔄 Update", key=f"upd_{unique_key}"):
            update_user(user, approved, limit)

        if cols[2].button("🗑️ Delete", key=f"del_{unique_key}"):
            delete_user(user)

def update_user(user, approved, limit):
    try:
        user_table.update_item(
            Key={"u_id": user["u_id"], "u_email": user["u_email"]},
            UpdateExpression="SET is_approved = :a, pdf_limit = :l",
            ExpressionAttributeValues={
                ":a": approved,
                ":l": int(limit)
            }
        )
        st.success("🔄 User updated!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Update failed: {str(e)}")

def delete_user(user):
    try:
        file_keys = [pdf["file_key"] if isinstance(pdf, dict) else pdf for pdf in user.get("pdf_files", [])]
        if file_keys:
            s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": [{"Key": key} for key in file_keys]})
        user_table.delete_item(Key={"u_id": user["u_id"], "u_email": user["u_email"]})
        st.success("🗑️ User deleted!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Deletion failed: {str(e)}")

def handle_pdf_management(users):
    if not users:
        st.warning("👥 No users found")
        return

    user = select_user(users)
    if user:
        u_id, u_email = user
        try:
            user_data = get_user_data(u_id, u_email)
            pdfs = process_pdf_entries(user_data.get("pdf_files", []))
            show_user_stats(user_data, u_email, pdfs)
            show_pdf_upload_form(u_id, u_email, user_data)
            show_stored_pdfs(pdfs, u_id, u_email)
        except ClientError as e:
            st.error(f"🚨 Access error: {str(e)}")


def select_user(users):
    return st.selectbox(
        "👤 Select User",
        [(u['u_id'], u['u_email']) for u in users],
        format_func=lambda x: f"{x[1]} ({x[0]})"
    )

def get_user_data(u_id, u_email):
    res = user_table.get_item(Key={"u_id": u_id, "u_email": u_email})
    return res.get("Item", {})

def show_user_stats(data, email, pdfs):
    st.subheader(f"📁 {email}'s Documents")
    cols = st.columns(3)
    cols[0].metric("📚 File Limit", int(data.get("pdf_limit", Decimal(5))))
    cols[1].metric("📁 Current Files", len(pdfs))
    cols[2].metric("🔄 Last Active", data.get("last_login", "Never"))

def show_pdf_upload_form(u_id, u_email, data):
    with st.expander("📤 Upload New", expanded=False):
        with st.form("upload_form"):
            file = st.file_uploader("📄 Choose PDF", type="pdf")
            sector = st.selectbox("📂 Sector", list(SECTOR_CONFIG.values()))
            if st.form_submit_button("🚀 Upload"):
                if file:
                    upload_pdf(file, u_id, u_email, int(data.get("pdf_limit", Decimal(5))), sector)
                else:
                    st.warning("⚠️ Select a PDF")

def show_stored_pdfs(pdfs, u_id, u_email):
    st.subheader("📂 Stored Documents")
    if pdfs:
        for pdf in pdfs:
            display_pdf_card(pdf, u_id, u_email)
            st.markdown("---")
    else:
        st.info("📭 No documents found")

def display_pdf_card(pdf, u_id, u_email):
    cols = st.columns([4, 2, 2, 1, 1])
    cols[0].markdown(f"**{pdf['filename']}**")
    cols[1].markdown(f"📂 {pdf['sector']}")
    cols[2].markdown(f"📅 {pd.to_datetime(pdf['upload_date']).strftime('%Y-%m-%d')}")
    cols[3].markdown(f"📦 {float(pdf.get('size', Decimal(0))) / 1e6:.1f}MB")
    cols[4].button("🗑️", key=f"del_{pdf['file_key']}",
                   on_click=delete_pdf, args=(u_id, u_email, pdf['file_key']))


def main():
    st.title("📚 Document Manager")
    st.markdown("---")
    
    if st.checkbox("🔓 Admin Dashboard"):
        with st.sidebar:
            st.subheader("⚙️ Admin Tools")
            if st.button("🔄 Migrate Files"):
                try:
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