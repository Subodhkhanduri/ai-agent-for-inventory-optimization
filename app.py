import streamlit as st
import uuid
import base64
import pandas as pd
from inventory_chatbot.frontend.ui_components import render_sidebar, render_message, render_forecast_table
from inventory_chatbot.frontend.api_client import APIClient

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(page_title="Inventory AI Assistant", layout="wide")
st.title("🤖 Inventory Management AI Assistant")
st.caption("Upload your inventory CSV and ask questions in natural language.")

# --------------------------
# SESSION STATE INIT
# --------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "token" not in st.session_state:
    st.session_state.token = None

if "role" not in st.session_state:
    st.session_state.role = "viewer"

session_id = st.session_state.session_id

# ================================
# SIDEBAR — AUTH + FILE UPLOAD
# ================================
uploaded_file = render_sidebar(session_id)

# ================================
# MAIN CHAT INTERFACE
# ================================
if uploaded_file is None:
    st.info("Please upload a CSV file in the sidebar to begin.")
else:
    # 0. SHOW CRITICAL ALERTS (1-Week Periodic Review)
    # Only calculate if we haven't already shown it to avoid re-running on every interaction
    # Or just run it - it's fast enough.
    
    with st.expander("⚠️ Critical Inventory Alerts (1-Week Periodic Review)", expanded=True):
        if "inventory_alerts" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
            with st.spinner("Analyzing inventory risks..."):
                alerts_data = APIClient.get_periodic_review(session_id)
                if "error" in alerts_data:
                    st.error(f"Failed to load alerts: {alerts_data['error']}")
                    st.session_state.inventory_alerts = None
                else:
                    st.session_state.inventory_alerts = alerts_data.get("data", [])
        
        alerts = st.session_state.inventory_alerts
        if alerts:
            df_alerts = pd.DataFrame(alerts)
            # Filter for ORDER required
            critical_items = df_alerts[df_alerts["Status"].str.contains("ORDER")]
            
            if not critical_items.empty:
                st.error(f"🚨 Action Required: {len(critical_items)} items need restocking!")
                st.dataframe(
                    critical_items[["Item", "Store", "Current Stock", "Target Level (T)", "Order Qty (Q)", "Status"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("✅ All inventory levels are healthy (1-Week Review).")
        else:
             st.info("No inventory data available for analysis.")

    st.divider()

    # 1. SHOW PREVIOUS MESSAGES
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"], msg.get("image"))

    # 2. USER INPUT
    if prompt := st.chat_input("Ask a question about your inventory…"):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_message("user", prompt)

        # Assistant response
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.write("Thinking...")

            data = APIClient.ask_question(prompt, session_id)

            if "error" in data:
                error_msg = f"❌ {data['error']}"
                placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                ai_response = data.get("response", "")
                forecast_values = data.get("forecast_values")
                chart_b64 = data.get("chart_b64")

                # Text response
                if ai_response:
                    placeholder.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # Forecast table
                if forecast_values:
                    render_forecast_table(forecast_values)

                # Chart
                if chart_b64:
                    st.image(base64.b64decode(chart_b64), caption="Visualization")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "",
                        "image": chart_b64
                    })

                if not ai_response and not chart_b64:
                    placeholder.warning("⚠ No useful response received from backend.")
