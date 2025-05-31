# Application Settings - Configuration management 
import os
from dotenv import load_dotenv
import logging

# Determine the project root directory dynamically
# This assumes settings.py is in a 'config' subdirectory of the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Construct the path to the .env file
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Load the .env file
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # This is a fallback for logging, actual critical warnings for missing keys are below
    logging.warning(f".env file not found at {ENV_PATH}. API keys and other secrets may not be loaded.")

# --- Gemini API Configuration ---
# If using a direct API key for Google AI Studio Gemini models
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# If planning to use a service account JSON for GCP (Vertex AI Gemini) later
# GOOGLE_APPLICATION_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")

# Critical check for Gemini API key
if not GEMINI_API_KEY:
    # Using print for immediate visibility during startup, logging might not be configured yet.
    print("CRITICAL WARNING: GEMINI_API_KEY is not set in .env. Gemini API will not function.")
    # You might want to raise an error here or handle it gracefully depending on how critical this is at startup
    # raise ValueError("CRITICAL WARNING: GEMINI_API_KEY is not set in .env. Gemini API will not function.")

# --- Database Configuration ---
SQLITE_DB_NAME = "agent_database.db"
# Ensures the 'data' directory is part of the path and it's at the project root
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', SQLITE_DB_NAME)}"

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.path.join(PROJECT_ROOT, 'data', 'logs')
LOG_FILE_PATH = os.path.join(LOG_DIR, 'app.log')

# Ensure log directory exists
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError as e:
        print(f"Error creating log directory {LOG_DIR}: {e}")

# --- Other API Keys (for later phases) ---
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY")
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")
# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

# --- Application Specific Settings ---
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Example of how to quickly test if settings are loaded (optional, remove after testing)
if __name__ == "__main__":
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Env Path: {ENV_PATH}")
    print(f"Gemini API Key Loaded: {'Yes' if GEMINI_API_KEY else 'No'}")
    print(f"Database URL: {DATABASE_URL}")
    print(f"Log File Path: {LOG_FILE_PATH}")
    # Create log directory if it doesn't exist, useful for file logging later
    if not os.path.exists(os.path.dirname(LOG_FILE_PATH)):
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True) 