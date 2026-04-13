# inventory_chatbot/api/endpoints.py

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
import base64
import re

from inventory_chatbot.analytics.core_analytics import (
    load_dataset_for_session,
    get_session_dataframe,
)
from inventory_chatbot.analytics.validator import DataValidator
from inventory_chatbot.services.cache_service import CacheService
from inventory_chatbot.services.auth_service import AuthService

router = APIRouter()

# Core services used by endpoints
validator = DataValidator()
cache = CacheService()
auth = AuthService()


# -------------------------------------------------------------------
# Helper: extract user role from Authorization header (JWT)
# -------------------------------------------------------------------
def get_user_role(request: Request) -> str:
    """
    Returns role from JWT token.
    If token missing/invalid -> treat as 'viewer'.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return "viewer"

    token = auth_header.replace("Bearer ", "").strip()

    try:
        payload = auth.decode_token(token)
        return payload.get("role", "viewer")
    except Exception:
        # Invalid token → safest to downgrade to viewer
        return "viewer"


# ==========================================================
# AUTH: Simple login (for future integration from frontend)
# ==========================================================
@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    user = auth.authenticate(username, password)
    if not user:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    username, role = user
    token = auth.create_token(username, role)
    return {
        "access_token": token,
        "role": role,
        "token_type": "bearer",
    }


# ==========================================================
# UPLOAD CSV
# ==========================================================
@router.post("/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    # (Optional) use RBAC here later if needed
    df = load_dataset_for_session(file, session_id)

    ok, messages = validator.validate(df)

    if not ok:
        return {
            "status": "error",
            "message": "Validation failed",
            "issues": messages,
        }

    return {
        "status": "success",
        "message": "File uploaded successfully",
        "session_id": session_id,
        "columns": list(df.columns),
        "validation": messages,
    }


# ==========================================================
# ASK ENDPOINT (CrewAI VERSION)
# ==========================================================
@router.post("/ask")
async def ask_question(request: Request):
    """
    Process user queries using CrewAI multi-agent system.
    The crew handles query analysis, data retrieval, forecasting,
    visualization, and response generation through agent collaboration.
    """
    data = await request.form()
    query = data.get("query")
    session_id = data.get("session_id")

    # ---------------------- Basic checks ----------------------
    if not query:
        return JSONResponse({"error": "Missing query"}, status_code=400)
    if not session_id:
        return JSONResponse({"error": "Missing session_id"}, status_code=400)

    df = get_session_dataframe(session_id)
    if df is None:
        return JSONResponse({"error": "No dataset found"}, status_code=400)

    # Get user role for RBAC
    role = get_user_role(request)

    # ---------------------- Check cache first ----------------------
    query_lower = query.lower()
    cache_key = f"crew:{session_id}:{hash(query_lower)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # ==========================================================
    # EXECUTE SIMPLE ORCHESTRATOR (NO CrewAI, NO OpenAI)
    # ==========================================================
    try:
        from inventory_chatbot.crew import SimpleInventoryOrchestrator
        
        # ---------------------- Get conversation history ----------------------
        history_key = f"history:{session_id}"
        conversation_history = cache.get(history_key) or []
        
        # Initialize orchestrator with context
        orchestrator = SimpleInventoryOrchestrator(
            dataframe=df,
            user_role=role,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        # Execute orchestrator to process query
        result = orchestrator.execute(query)
        
        # ---------------------- Update conversation history ----------------------
        if "error" not in result and result.get("response"):
            conversation_history.append({
                "query": query,
                "response": result.get("response", "")
            })
            # Keep only last 10 exchanges to avoid memory bloat
            cache.set(history_key, conversation_history[-10:], ttl=1800)  # 30 min TTL
        
        # Cache successful results
        if "error" not in result:
            cache.set(cache_key, result, ttl=600)
        
        return result

    except Exception as e:
        # Fallback error response
        return {
            "error": f"Query processing failed: {str(e)}",
            "status": "error"
        }

# ==========================================================
# INVENTORY BATCH REVIEW
# ==========================================================
@router.post("/inventory/periodic-review")
async def get_periodic_review(
    session_id: str = Form(...),
    lead_time: int = Form(7),
    service_level: float = Form(1.65),
    lead_time_std: float = Form(0.0)
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
        results_df = calculate_batch_periodic_review(df, lead_time_days=lead_time, service_level=service_level, lead_time_std=lead_time_std)
        
        if results_df.empty:
            return {"status": "empty", "data": []}
            
        # Convert to dict
        data = results_df.to_dict(orient="records")
        
        return {
            "status": "success", 
            "data": data,
            "count": len(data)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)
# ==========================================================
# INVENTORY COMPARISON (Fixed vs Uncertain Lead Time)
# ==========================================================
@router.post("/inventory/compare-lead-times")
async def compare_lead_times(
    session_id: str = Form(...),
    lead_time: int = Form(7),
    service_level: float = Form(1.65),
    lead_time_std: float = Form(None)  # Optional, will use historical if None
):
    """
    Compare Fixed vs Uncertain Lead Time scenarios.
    """
    df = get_session_dataframe(session_id)
    if df is None:
        return JSONResponse({"error": "No dataset found"}, status_code=404)
        
    try:
        from inventory_chatbot.analytics.inventory_calculator import compare_lead_time_scenarios
        
        # Run comparison
        result = compare_lead_time_scenarios(
            df, 
            lead_time_days=lead_time, 
            service_level=service_level, 
            user_lead_time_std=lead_time_std
        )
        
        if "error" in result:
            return JSONResponse({"error": result["error"]}, status_code=400)
            
        return {
            "status": "success", 
            "comparison": result
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)
