import sys

def replace_in_file(filepath, tgt, repl):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if tgt in content:
        content = content.replace(tgt, repl)
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"Success: {filepath}")
    else:
        print(f"Failed to find target in {filepath}")

# 1. api_client.py
tgt1 = '''    @staticmethod
    def get_periodic_review(session_id):
        """Get batch inventory review."""
        try:
            response = requests.post(
                f"{BACKEND_URL}/inventory/periodic-review",
                data={"session_id": session_id},'''
rep1 = '''    @staticmethod
    def get_periodic_review(session_id, lead_time=7, service_level=1.65):
        """Get batch inventory review."""
        try:
            response = requests.post(
                f"{BACKEND_URL}/inventory/periodic-review",
                data={"session_id": session_id, "lead_time": lead_time, "service_level": service_level},'''
replace_in_file(r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\frontend\api_client.py", tgt1, rep1)

# 2. endpoints.py
tgt2 = '''@router.post("/inventory/periodic-review")
async def get_periodic_review(
    session_id: str = Form(...)
):
    """
    Get batch periodic review for all items in the session dataset.
    """
    df = get_session_dataframe(session_id)
    if df is None:
        return JSONResponse({"error": "No dataset found"}, status_code=404)
        
    try:
        from inventory_chatbot.analytics.inventory_calculator import calculate_batch_periodic_review
        
        # Run calculation
        results_df = calculate_batch_periodic_review(df)'''

rep2 = '''@router.post("/inventory/periodic-review")
async def get_periodic_review(
    session_id: str = Form(...),
    lead_time: int = Form(7),
    service_level: float = Form(1.65)
):
    """
    Get batch periodic review for all items in the session dataset.
    """
    df = get_session_dataframe(session_id)
    if df is None:
        return JSONResponse({"error": "No dataset found"}, status_code=404)
        
    try:
        from inventory_chatbot.analytics.inventory_calculator import calculate_batch_periodic_review
        
        # Run calculation
        results_df = calculate_batch_periodic_review(df, lead_time_days=lead_time, service_level=service_level)'''
replace_in_file(r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\api\endpoints.py", tgt2, rep2)

# 3. inventory_calculator.py
tgt3 = '''def calculate_batch_periodic_review(df: pd.DataFrame, review_period_days: int = 7) -> pd.DataFrame:
    """
    Run Periodic Review System calculation for ALL items in the DataFrame.
    Returns a summary DataFrame with key metrics, sorted by urgency.
    """
    results = []
    
    # Get unique item-store pairs
    if "Item" not in df.columns or "Store" not in df.columns:
        return pd.DataFrame()

    pairs = df[["Item", "Store"]].drop_duplicates().to_dict('records')
    
    for pair in pairs:
        res = calculate_periodic_review_status(
            df=df,
            item=pair["Item"],
            store=pair["Store"],
            review_period_days=review_period_days
        )'''

rep3 = '''def calculate_batch_periodic_review(df: pd.DataFrame, review_period_days: int = 7, lead_time_days: int = 7, service_level: float = 1.65) -> pd.DataFrame:
    """
    Run Periodic Review System calculation for ALL items in the DataFrame.
    Returns a summary DataFrame with key metrics, sorted by urgency.
    """
    results = []
    
    # Get unique item-store pairs
    if "Item" not in df.columns or "Store" not in df.columns:
        return pd.DataFrame()

    pairs = df[["Item", "Store"]].drop_duplicates().to_dict('records')
    
    for pair in pairs:
        res = calculate_periodic_review_status(
            df=df,
            item=pair["Item"],
            store=pair["Store"],
            review_period_days=review_period_days,
            lead_time_days=lead_time_days,
            service_level=service_level
        )'''
replace_in_file(r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\analytics\inventory_calculator.py", tgt3, rep3)

# 4. app.py
tgt4 = '''    with st.expander("⚠️ Critical Inventory Alerts (1-Week Periodic Review)", expanded=True):
        if "inventory_alerts" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
            with st.spinner("Analyzing inventory risks..."):
                alerts_data = APIClient.get_periodic_review(session_id)'''

rep4 = '''    with st.expander("⚠️ Critical Inventory Alerts (1-Week Periodic Review)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            ui_lead_time = st.slider("Lead Time (Days)", 1, 30, 7, help="Estimated days for supplier restocks to arrive.")
        with col2:
            ui_service_options = {"Conservative (90% availability)": 1.28, "Standard (95% availability)": 1.65, "Aggressive (99% availability)": 2.33}
            ui_service = st.selectbox("Service Level Strategy", list(ui_service_options.keys()), index=1, help="Buffer margin against variance in demand.")
            ui_service_level = ui_service_options[ui_service]
            
        settings_key = f"{uploaded_file.name}-{ui_lead_time}-{ui_service_level}"

        if "inventory_alerts" not in st.session_state or st.session_state.get("last_settings_key") != settings_key:
            with st.spinner("Analyzing inventory risks..."):
                st.session_state.last_settings_key = settings_key
                alerts_data = APIClient.get_periodic_review(session_id, ui_lead_time, ui_service_level)'''
replace_in_file(r"d:\MTP2\conversational-inventory-ai-main\app.py", tgt4, rep4)
