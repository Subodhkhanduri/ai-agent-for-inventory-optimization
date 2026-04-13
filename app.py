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

        col1, col2, col3 = st.columns(3)

        with col1:

            ui_lead_time = st.slider("Lead Time (Days)", 1, 30, 7, help="Estimated days for supplier restocks to arrive.")

        with col2:

            ui_lead_time_std = st.slider("Lead Time Std Dev (Days)", 0.0, 10.0, 0.0, step=0.1, help="Variance in lead time to calculate uncertainty.")

        with col3:

            ui_service_options = {"Conservative (90% availability)": 1.28, "Standard (95% availability)": 1.65, "Aggressive (99% availability)": 2.33}

            ui_service = st.selectbox("Service Level Strategy", list(ui_service_options.keys()), index=1, help="Buffer margin against variance in demand.")

            ui_service_level = ui_service_options[ui_service]

            

        settings_key = f"{uploaded_file.name}-{ui_lead_time}-{ui_lead_time_std}-{ui_service_level}"

        if "inventory_alerts" not in st.session_state or st.session_state.get("last_settings_key") != settings_key:
            with st.spinner("Analyzing inventory risks..."):
                st.session_state.last_settings_key = settings_key

                alerts_data = APIClient.get_periodic_review(session_id, ui_lead_time, ui_service_level, ui_lead_time_std)
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
                
                # Check for ROP in columns to support legacy session state caches safely
                cols_to_show = ["Item", "Store", "Current Stock", "Target Level (T)", "Order Qty (Q)", "Status"]
                if "ROP" in critical_items.columns:
                    cols_to_show.insert(3, "ROP")
                
                st.dataframe(
                    critical_items[cols_to_show],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("✅ All inventory levels are healthy (1-Week Review).")
        else:
             st.info("No inventory data available for analysis.")

    with st.expander("⚖️ Strategy Comparison: Fixed vs. Uncertain Lead Time", expanded=True):
        if st.session_state.get("inventory_alerts"):
            with st.spinner("Comparing strategies..."):
                comp_data = APIClient.get_lead_time_comparison(session_id, ui_lead_time, ui_service_level, ui_lead_time_std)
                
                if "error" in comp_data:
                    st.error(f"Comparison failed: {comp_data.get('error', 'Unknown error')}")
                else:
                    comparison = comp_data.get("comparison", {})
                    summary = comparison.get("summary", {})
                    items = comparison.get("item_comparison", [])
                    
                    if not items:
                        st.info("No items to compare.")
                    else:
                        df_comp = pd.DataFrame(items)
                        
                        # 1. Recommendation Alert
                        if "Uncertain" in summary.get("recommendation", ""):
                            st.info(f"💡 **Recommendation: {summary['recommendation']}**\n\n{summary['justification']}")
                        else:
                            st.success(f"✅ **Recommendation: {summary.get('recommendation', 'Fixed Lead Time')}**\n\n{summary.get('justification', '')}")
                        
                        # 2. High-level Metrics
                        m1, m2, m3 = st.columns(3)
                        avg_ss_fixed = df_comp["Safety Stock_fixed"].mean()
                        avg_ss_unc = df_comp["Safety Stock_uncertain"].mean()
                        ss_diff = ((avg_ss_unc - avg_ss_fixed) / avg_ss_fixed * 100) if avg_ss_fixed > 0 else 0
                        
                        m1.metric("Historical Lead Time StdDev", f"{summary.get('historical_std', 0)} days")
                        m2.metric("Avg Safety Stock (Fixed)", f"{avg_ss_fixed:.1f}")
                        m3.metric("Avg Safety Stock (Uncertain)", f"{avg_ss_unc:.1f}", f"+{ss_diff:.1f}% cost" if ss_diff > 0 else "0%")
                        
                        # 3. Detailed Comparison table
                        st.subheader("Item-by-Item Comparison")
                        display_df = df_comp[["Item", "Store", "Safety Stock_fixed", "Safety Stock_uncertain", "Status_fixed", "Status_uncertain"]].copy()
                        display_df.columns = ["Item", "Store", "SS (Fixed)", "SS (Uncertain)", "Status (Fixed)", "Status (Uncertain)"]
                        display_df["SS Increase"] = display_df["SS (Uncertain)"] - display_df["SS (Fixed)"]
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Upload data to see strategy comparison.")

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
