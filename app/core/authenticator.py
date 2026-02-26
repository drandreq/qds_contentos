import os
import logging
from typing import Optional, Dict, Any
from google import genai
import google.auth
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)

class GoogleAIAuthenticator:
    """
    Dual-layer authentication for Google AI SDK:
    1. Check for explicit GOOGLE_API_KEY in environment.
    2. Fallback to Google Cloud Application Default Credentials (ADC).
    """

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.auth_layer_used: str = "none"

    def initialize(self) -> genai.Client:
        """
        Initializes the Google GenAI client using the dual-layer strategy.
        Returns the initialized client.
        """
        # Layer 1: Explicit API Key (Dev/Fallback)
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key and api_key != "your_google_api_key_here":
            logger.info("Initializing Google AI SDK via explicit API Key (Layer 1).")
            self.client = genai.Client(api_key=api_key)
            self.auth_layer_used = "api_key"
            return self.client

        # Layer 2: Application Default Credentials (Production via Sidecar)
        logger.info("No valid GOOGLE_API_KEY found. Attempting to use ADC (Layer 2).")
        try:
            # Verify ADC is actually available in the environment
            credentials, project_id = google.auth.default()
            logger.info(f"ADC discovered for project: {project_id}")
            
            # The genai.Client() with no args automatically picks up ADC
            # when running in Vertex AI mode or if the environment is configured correctly.
            # To strictly use the Gemini Developer API through ADC, we just initialize empty.
            self.client = genai.Client()
            self.auth_layer_used = "adc"
            return self.client
            
        except DefaultCredentialsError as e:
            logger.error(f"Failed to initialize ADC: {e}")
            self.auth_layer_used = "failed"
            raise RuntimeError(
                "Could not initialize Google GenAI client. Neither GOOGLE_API_KEY "
                "nor Application Default Credentials were valid."
            ) from e

    def get_status(self) -> Dict[str, Any]:
        """Returns the current authentication status for health checks."""
        return {
            "initialized": self.client is not None,
            "auth_layer": self.auth_layer_used
        }

# Global singleton instance to be initialized during FastAPI lifespan
authenticator = GoogleAIAuthenticator()
