# inspect_lgbm.py
import pickle
import os

model_path = "models/global_lgbm_model.pkl"

if os.path.exists(model_path):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
        
    print(f"Model type: {type(model)}")
    
    # Try to get feature names
    if hasattr(model, "feature_name"):
        print("Feature names:")
        print(model.feature_name())
    elif hasattr(model, "booster_"):
        print("Feature names from booster:")
        print(model.booster_.feature_name())
    elif hasattr(model, "feature_names_in_"):
        print("Feature names (scikit-learn style):")
        print(model.feature_names_in_)
    else:
        print("Could not find feature names on the model object.")
else:
    print("Model file not found.")
