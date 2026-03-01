# inventory_chatbot/services/llm_service.py

import time
import logging
from typing import Optional
from groq import Groq
from inventory_chatbot.config import settings


# ------------------------------------------------------------
# LOGGER SETUP
# ------------------------------------------------------------
logger = logging.getLogger("LLMService")
logger.setLevel(logging.INFO)


class LLMService:
    """
    Production-ready LLM service wrapper for Groq.
    - Automatic model fallback
    - Retry logic
    - Token usage logging
    - Timeout controls
    - Clean error messages
    """

    PRIMARY_MODEL = settings.GROQ_MODEL                     # "llama-3.1-8b-instant"
    FALLBACK_MODEL = "llama-3.1-70b-versatile"             # fallback model

    def __init__(self):
        try:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq LLM client initialized successfully")
            logger.info(f"Using model: {self.PRIMARY_MODEL}")
        except Exception as e:
            logger.error(f"🔥 Failed to initialize Groq: {e}")
            raise


    # --------------------------------------------------------
    # INTERNAL: ROBUST LLM CALL
    # --------------------------------------------------------
    def _call_llm(self, model: str, messages: list) -> str:
        """
        Performs a Groq LLM call with retries and logging.
        """

        MAX_RETRIES = 3
        RETRY_DELAY = 1.2  # seconds

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=800,
                    temperature=0.15,
                    timeout=15,
                )

                # Extract Assistant Text
                msg = response.choices[0].message.content

                # Token usage logs
                if hasattr(response, "usage") and response.usage:
                    usage = response.usage
                    logger.info(
                        f"LLM Usage → prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
                    )

                return msg

            except Exception as e:
                logger.error(
                    f"[Attempt {attempt}/{MAX_RETRIES}] LLM error ({model}): {e}"
                )

            time.sleep(RETRY_DELAY)

        raise RuntimeError(f"❌ LLM request failed after {MAX_RETRIES} retries.")


    # --------------------------------------------------------
    # HIGH LEVEL SAFE INTERFACE WITH FALLBACK
    # --------------------------------------------------------
    def generate_response(self, prompt: str) -> str:
        """
        Sends prompt using primary model → fallback model if needed.
        """

        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ]

        # Primary model attempt
        try:
            return self._call_llm(self.PRIMARY_MODEL, messages)

        except Exception as e:
            logger.warning(
                f"⚠ Primary model '{self.PRIMARY_MODEL}' failed → trying fallback '{self.FALLBACK_MODEL}'"
            )

        # Fallback model
        try:
            return self._call_llm(self.FALLBACK_MODEL, messages)

        except Exception as e2:
            logger.error(f"🔥 Fallback model failed as well: {e2}")
            return "⚠ The AI model is temporarily unavailable. Please try again later."


    # --------------------------------------------------------
    # EXPECTED BY endpoints.py
    # --------------------------------------------------------
    def chat(self, user_input: str, system_prompt: str = "") -> str:
        """
        Combines system + user input and sends to Groq.
        """

        final_prompt = ""

        if system_prompt:
            final_prompt += system_prompt.strip() + "\n\n"

        final_prompt += f"User: {user_input.strip()}"

        return self.generate_response(final_prompt)
