import re

path = r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\analytics\inventory_calculator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

tgt_pattern = r"def calculate_batch_periodic_review\(df: pd\.DataFrame, review_period_days: int = 7\) -> pd\.DataFrame:.*?for pair in pairs:\s*res = calculate_periodic_review_status\(\s*df=df,\s*item=pair\[\"Item\"\],\s*store=pair\[\"Store\"\],\s*review_period_days=review_period_days\s*\)"

repl = '''def calculate_batch_periodic_review(df: pd.DataFrame, review_period_days: int = 7, lead_time_days: int = 7, service_level: float = 1.65) -> pd.DataFrame:
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

sub = re.sub(tgt_pattern, repl, content, flags=re.DOTALL)

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(sub)
print("done")
