# inventory_chatbot/frontend/api_client.py

import requests
import streamlit as st

import os

# Read from environment, fallback to localhost for local dev
BACKEND_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

class APIClient:
    """Handles all communication with the FastAPI backend."""

    @staticmethod
    def get_headers():
        """Get auth headers from session state."""
        headers = {}
        if st.session_state.get("token"):
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        return headers

    @staticmethod
    def login(username, password):
        """Authenticate user."""
        try:
            resp = requests.post(
                f"{BACKEND_URL}/login",
                data={"username": username, "password": password},
            )
            return resp.json()
        except Exception as e:
            return {"error": f"Connection failed: {e}"}

    @staticmethod
    def upload_file(uploaded_file, session_id):
        """Upload inventory CSV."""
        try:
            response = requests.post(
                f"{BACKEND_URL}/upload",
                data={"session_id": session_id},
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")},
                headers=APIClient.get_headers(),
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def ask_question(query, session_id):
        """Send natural language query to backend."""
        try:
            response = requests.post(
                f"{BACKEND_URL}/ask",
                data={"query": query, "session_id": session_id},
                headers=APIClient.get_headers(),
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_periodic_review(session_id, lead_time=7, service_level=1.65):
        """Get batch inventory review."""
        try:
            response = requests.post(
                f"{BACKEND_URL}/inventory/periodic-review",
                data={"session_id": session_id, "lead_time": lead_time, "service_level": service_level},
                headers=APIClient.get_headers(),
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
