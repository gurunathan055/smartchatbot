import os

# --- General Bot Configuration ---
# Microsoft App ID and Password (for Bot Framework Adapter in app.py)
APP_ID = os.environ.get("MicrosoftAppId", "")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")

# --- CLU Configuration (for NLU in simple_bot.py) ---
# These would be used if CLU interaction were not mocked.
CLU_ENDPOINT = os.environ.get("CLU_ENDPOINT", "YOUR_CLU_ENDPOINT_PLACEHOLDER")
CLU_KEY = os.environ.get("CLU_KEY", "YOUR_CLU_API_KEY_PLACEHOLDER")
CLU_PROJECT_NAME = os.environ.get("CLU_PROJECT_NAME", "YOUR_CLU_PROJECT_NAME_PLACEHOLDER")
CLU_DEPLOYMENT_NAME = os.environ.get("CLU_DEPLOYMENT_NAME", "YOUR_CLU_DEPLOYMENT_NAME_PLACEHOLDER")

# --- Freshdesk Configuration (for freshdesk_client.py and simple_bot.py) ---
FRESHDESK_API_KEY = os.environ.get("FRESHDESK_API_KEY", "YOUR_FRESHDESK_API_KEY_PLACEHOLDER")
FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN", "YOUR_FRESHDESK_DOMAIN_PLACEHOLDER.freshdesk.com")
TEST_FRESHDESK_TICKET_ID = int(os.environ.get("TEST_FRESHDESK_TICKET_ID", "1"))
BOT_FRESHDESK_USER_ID_STR = os.environ.get("BOT_FRESHDESK_USER_ID", "YOUR_BOT_FRESHDESK_AGENT_ID_PLACEHOLDER")

try:
    BOT_FRESHDESK_USER_ID = int(BOT_FRESHDESK_USER_ID_STR)
except ValueError:
    BOT_FRESHDESK_USER_ID = "YOUR_BOT_FRESHDESK_AGENT_ID_PLACEHOLDER"

USE_MOCKED_FRESHDESK = (
    FRESHDESK_API_KEY == "YOUR_FRESHDESK_API_KEY_PLACEHOLDER" or
    FRESHDESK_DOMAIN == "YOUR_FRESHDESK_DOMAIN_PLACEHOLDER.freshdesk.com" or
    not isinstance(BOT_FRESHDESK_USER_ID, int)
)

# ID of the Freshdesk business hour configuration to check against.
# This is a string because the API expects it as part of the URL.
FRESHDESK_BUSINESS_HOUR_ID = os.environ.get("FRESHDESK_BUSINESS_HOUR_ID", "YOUR_FRESHDESK_BUSINESS_HOUR_ID_PLACEHOLDER")

# Optional: Default Group ID for ticket assignment during handover
HANDOVER_GROUP_ID_STR = os.environ.get("HANDOVER_GROUP_ID", "")
try:
    HANDOVER_GROUP_ID = int(HANDOVER_GROUP_ID_STR) if HANDOVER_GROUP_ID_STR else None
except ValueError:
    HANDOVER_GROUP_ID = None # Or some other default if parsing fails

# Optional: Default Agent ID for ticket assignment during handover
HANDOVER_AGENT_ID_STR = os.environ.get("HANDOVER_AGENT_ID", "")
try:
    HANDOVER_AGENT_ID = int(HANDOVER_AGENT_ID_STR) if HANDOVER_AGENT_ID_STR else None
except ValueError:
    HANDOVER_AGENT_ID = None # Or some other default if parsing fails

# Status ID for "Pending" in Freshdesk (typically 3, but configurable if needed)
FRESHDESK_PENDING_STATUS_ID = int(os.environ.get("FRESHDESK_PENDING_STATUS_ID", "3"))


# --- Salesforce Configuration (for salesforce_client.py and simple_bot.py) ---
SALESFORCE_CLIENT_ID = os.environ.get("SALESFORCE_CLIENT_ID", "YOUR_SALESFORCE_CLIENT_ID_PLACEHOLDER")
SALESFORCE_CLIENT_SECRET = os.environ.get("SALESFORCE_CLIENT_SECRET", "YOUR_SALESFORCE_CLIENT_SECRET_PLACEHOLDER")
SALESFORCE_USERNAME = os.environ.get("SALESFORCE_USERNAME", "YOUR_SALESFORCE_USERNAME_PLACEHOLDER")
SALESFORCE_PASSWORD = os.environ.get("SALESFORCE_PASSWORD", "YOUR_SALESFORCE_PASSWORD_TOKEN_PLACEHOLDER")
SALESFORCE_LOGIN_URL = os.environ.get("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")

USE_MOCKED_SALESFORCE = (
    SALESFORCE_CLIENT_ID == "YOUR_SALESFORCE_CLIENT_ID_PLACEHOLDER" or
    SALESFORCE_CLIENT_SECRET == "YOUR_SALESFORCE_CLIENT_SECRET_PLACEHOLDER" or
    SALESFORCE_USERNAME == "YOUR_SALESFORCE_USERNAME_PLACEHOLDER" or
    SALESFORCE_PASSWORD == "YOUR_SALESFORCE_PASSWORD_TOKEN_PLACEHOLDER"
)

# --- Snowflake Configuration (for snowflake_client.py and simple_bot.py) ---
SNOWFLAKE_USER = os.environ.get("SNOWFLAKE_USER", "YOUR_SNOWFLAKE_USER_PLACEHOLDER")
SNOWFLAKE_PASSWORD = os.environ.get("SNOWFLAKE_PASSWORD", "") # Optional, if using key-pair
SNOWFLAKE_ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT_PLACEHOLDER") # e.g., youraccount or xy12345.us-east-1
SNOWFLAKE_WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "YOUR_SNOWFLAKE_WAREHOUSE_PLACEHOLDER")
SNOWFLAKE_DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "YOUR_SNOWFLAKE_DATABASE_PLACEHOLDER")
SNOWFLAKE_SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA", "YOUR_SNOWFLAKE_SCHEMA_PLACEHOLDER")
SNOWFLAKE_ROLE = os.environ.get("SNOWFLAKE_ROLE", "") # Optional

# For Key-Pair Authentication
SNOWFLAKE_PRIVATE_KEY_PATH = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "") # Path to your private key file
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "") # Passphrase if key is encrypted

USE_MOCKED_SNOWFLAKE = (
    SNOWFLAKE_USER == "YOUR_SNOWFLAKE_USER_PLACEHOLDER" or
    SNOWFLAKE_ACCOUNT == "YOUR_SNOWFLAKE_ACCOUNT_PLACEHOLDER" or
    (not SNOWFLAKE_PRIVATE_KEY_PATH and not SNOWFLAKE_PASSWORD) # Need either key or password for non-mocked
)


# --- Logging Configuration ---
print("--- Configuration Loaded ---")
print(f"  Freshdesk Domain: {FRESHDESK_DOMAIN}")
print(f"  Test Freshdesk Ticket ID: {TEST_FRESHDESK_TICKET_ID}")
print(f"  Bot's Freshdesk User ID: {BOT_FRESHDESK_USER_ID} (Type: {type(BOT_FRESHDESK_USER_ID)})")
print(f"  USE_MOCKED_FRESHDESK: {USE_MOCKED_FRESHDESK}")
print(f"  Freshdesk API Key Loaded: {'Yes' if FRESHDESK_API_KEY != 'YOUR_FRESHDESK_API_KEY_PLACEHOLDER' else 'No (Using Placeholder)'}")
print(f"  Freshdesk Business Hour ID: {FRESHDESK_BUSINESS_HOUR_ID}")
print(f"  Freshdesk Handover Group ID: {HANDOVER_GROUP_ID}")
print(f"  Freshdesk Handover Agent ID: {HANDOVER_AGENT_ID}")
print(f"  Freshdesk Pending Status ID: {FRESHDESK_PENDING_STATUS_ID}")
print("-" * 20)
print(f"  Salesforce Login URL: {SALESFORCE_LOGIN_URL}")
print(f"  Salesforce Client ID Loaded: {'Yes' if SALESFORCE_CLIENT_ID != 'YOUR_SALESFORCE_CLIENT_ID_PLACEHOLDER' else 'No (Using Placeholder)'}")
print(f"  Salesforce Username Loaded: {'Yes' if SALESFORCE_USERNAME != 'YOUR_SALESFORCE_USERNAME_PLACEHOLDER' else 'No (Using Placeholder)'}")
print(f"  USE_MOCKED_SALESFORCE: {USE_MOCKED_SALESFORCE}")
print("-" * 20)
print(f"  Snowflake User: {SNOWFLAKE_USER}")
print(f"  Snowflake Account: {SNOWFLAKE_ACCOUNT}")
print(f"  Snowflake Warehouse: {SNOWFLAKE_WAREHOUSE}")
print(f"  Snowflake Private Key Path Set: {'Yes' if SNOWFLAKE_PRIVATE_KEY_PATH else 'No'}")
print(f"  Snowflake Password Set: {'Yes' if SNOWFLAKE_PASSWORD else 'No'}")
print(f"  USE_MOCKED_SNOWFLAKE: {USE_MOCKED_SNOWFLAKE}")
print("--- End Configuration ---")
