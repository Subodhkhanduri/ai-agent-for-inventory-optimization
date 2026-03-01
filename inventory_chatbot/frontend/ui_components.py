# inventory_chatbot/frontend/ui_components.py

import base64
import pandas as pd
import streamlit as st
from inventory_chatbot.frontend.api_client import APIClient

def render_sidebar(session_id):
    """Render the auth and upload sidebar."""
    with st.sidebar:
        st.header("🔐 User Login")
        
        if st.session_state.token is None:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                res = APIClient.login(username, password)
                if "access_token" in res:
                    st.session_state.token = res["access_token"]
                    st.session_state.role = res["role"]
                    st.success(f"✅ Logged in as {res['role']}")
                    st.rerun()
                else:
                    st.error(f"❌ {res.get('error', 'Invalid credentials')}")
        else:
            st.success(f"✅ Logged in as: {st.session_state.role}")
            if st.button("Logout"):
                st.session_state.token = None
                st.session_state.role = "viewer"
                st.session_state.messages = []
                st.rerun()

        st.divider()
        st.header("📂 Upload Your Data")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        
        if uploaded_file is not None:
            if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
                with st.spinner("Uploading and validating file..."):
                    res = APIClient.upload_file(uploaded_file, session_id)
                    
                    if res.get("status") == "error":
                        st.error("❌ File validation failed")
                        for issue in res.get("issues", []):
                            st.warning(issue)
                    else:
                        st.success("✅ File uploaded successfully!")
                        st.info("Columns detected: " + ", ".join(res.get("columns", [])))
                        st.session_state.messages = []
                        st.session_state.last_uploaded = uploaded_file.name

        st.divider()
        st.caption("Role permissions:")
        st.caption("• viewer → chat & stats")
        st.caption("• manager/admin → forecasting")
        
        return uploaded_file

def render_message(role, content, image_b64=None):
    """Render a single chat message."""
    with st.chat_message(role):
        if content:
            st.write(content)
        if image_b64:
            st.image(base64.b64decode(image_b64), caption="Visualization")

def render_forecast_table(forecast_values):
    """Render the forecast table."""
    if forecast_values:
        df_forecast = pd.DataFrame(forecast_values)
        st.subheader("📈 Forecast Table")
        st.dataframe(df_forecast)
