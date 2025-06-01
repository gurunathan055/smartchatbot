# End-to-End Testing Configuration

This document outlines the necessary configurations for testing the Azure Bot to Freshdesk integration.

## 1. Azure Bot (`simple_bot.py` via `config.py`)

These settings are primarily managed in `config.py` and should be set as environment variables.

*   **`FRESHDESK_API_KEY`**:
    *   **Description**: Your Freshdesk account's API key. Used for authenticating API requests to Freshdesk.
    *   **Source**: Freshdesk Admin Portal (Profile Settings).
    *   **Example**: `YOUR_API_KEY_PLACEHOLDER` (replace with actual key for live testing)

*   **`FRESHDESK_DOMAIN`**:
    *   **Description**: Your full Freshdesk domain name.
    *   **Source**: Your Freshdesk account URL.
    *   **Example**: `YOUR_DOMAIN_PLACEHOLDER.freshdesk.com` (replace with actual domain)

*   **`TEST_FRESHDESK_TICKET_ID`**:
    *   **Description**: A default Freshdesk ticket ID used for testing replies directly from the bot when not triggered by a Freshdesk webhook (e.g., when testing from Bot Framework Emulator with an intent that sends to Freshdesk).
    *   **Source**: An existing ticket ID in your Freshdesk instance.
    *   **Example**: `1` (replace with a valid ticket ID)

*   **`BOT_FRESHDESK_USER_ID`**:
    *   **Description**: The numerical ID of an existing agent user in Freshdesk that will represent the bot when it posts replies/notes. This ID is used in the `user_id` field of the Freshdesk API when sending a reply.
    *   **Source**: Freshdesk Admin > Agents. The ID might be visible in the URL when viewing an agent's profile, or obtainable via the Agent API.
    *   **Example**: `YOUR_BOT_AGENT_ID_PLACEHOLDER` (replace with a valid agent ID, must be an integer)

*   **`FRESHDESK_BUSINESS_HOUR_ID`**:
    *   **Description**: The ID of the Business Hours configuration in your Freshdesk account that the bot should check against. This is a string (e.g., "1234567890").
    *   **Source**: Freshdesk Admin > Admin > Support Operations > Business Hours. The ID is usually visible in the URL when editing a specific business hour configuration.
    *   **Example**: `"YOUR_FRESHDESK_BUSINESS_HOUR_ID_PLACEHOLDER"` (replace with actual ID for live testing or leave as placeholder to use mocked business hours).
    *   **Mocked Behavior**: If this is the placeholder or not set, `freshdesk_client.get_freshdesk_business_hours` will return a mocked "always open" or "always closed" schedule (see `freshdesk_client.py` for specifics).

*   **`HANDOVER_GROUP_ID`** (Optional):
    *   **Description**: The numerical ID of a default Freshdesk Group to which tickets should be assigned during a bot-initiated handover.
    *   **Source**: Freshdesk Admin > Admin > Team > Groups. The ID might be visible in the URL or via the Groups API.
    *   **Example**: `""` (empty string if not used), or an integer like `1234567890`. If empty, no group assignment will be attempted by default during handover.

*   **`HANDOVER_AGENT_ID`** (Optional):
    *   **Description**: The numerical ID of a default Freshdesk Agent to whom tickets should be assigned during a bot-initiated handover. Note: Assigning directly to an agent might override group assignments or round-robin logic.
    *   **Source**: Freshdesk Admin > Admin > Team > Agents.
    *   **Example**: `""` (empty string if not used), or an integer like `9876543210`. If empty, no specific agent assignment will be attempted by default.

*   **`FRESHDESK_PENDING_STATUS_ID`**:
    *   **Description**: The numerical ID representing the "Pending" status in Freshdesk. This is used when the bot hands over a ticket.
    *   **Source**: Standard Freshdesk status. Typically 3, but can be configured if your Freshdesk instance uses a different ID for "Pending".
    *   **Example**: `"3"` (default)

*   **`CLU_ENDPOINT`**, **`CLU_KEY`**, **`CLU_PROJECT_NAME`**, **`CLU_DEPLOYMENT_NAME`**:
    *   **Description**: Configuration for Azure AI Language Conversational Language Understanding (CLU) service. Currently, CLU interaction is mocked in `simple_bot.py`. For real NLU, these would be required.
    *   **Source**: Your Azure AI Language resource and CLU project deployment.
    *   **Example**: Placeholders like `YOUR_CLU_ENDPOINT`

*   **`MicrosoftAppId` (for `APP_ID` in `config.py`)**:
    *   **Description**: The Microsoft App ID of your Azure Bot. Used by the Bot Framework Adapter. Can be blank for local testing if the emulator/channel doesn't strictly require it.
    *   **Source**: Azure Bot registration.
    *   **Example**: (GUID, e.g., `abcdef12-3456-7890-abcd-ef1234567890`)

*   **`MicrosoftAppPassword` (for `APP_PASSWORD` in `config.py`)**:
    *   **Description**: The Microsoft App Password for your Azure Bot. Used by the Bot Framework Adapter.
    *   **Source**: Azure Bot registration.
    *   **Example**: (Your bot's app password)

**Note on `USE_MOCKED_FRESHDESK` in `config.py`:**
This flag will automatically be set to `True` if `FRESHDESK_API_KEY`, `FRESHDESK_DOMAIN` are placeholders, or if `BOT_FRESHDESK_USER_ID` is not a valid integer. This allows running the bot and function without live Freshdesk credentials, in which case Freshdesk API calls will be simulated.

## 2. Azure Function (`HttpFreshdeskWebhookTrigger`)

These settings are for the Azure Function that acts as an intermediary, receiving simulated Freshdesk webhooks and forwarding them to the bot. They should be set as Application Settings in Azure Portal or in `local.settings.json` for local development.

*   **`BOT_ENDPOINT_URL`**:
    *   **Description**: The publicly accessible messaging endpoint of your Azure Bot. The Azure Function will POST transformed activities to this URL.
    *   **Source**: If bot is local, this will be your ngrok URL (e.g., `https://your-ngrok-id.ngrok.io/api/messages`). If deployed, it's your Azure App Service URL for the bot (e.g., `https://your-bot-name.azurewebsites.net/api/messages`).
    *   **Example**: `http://localhost:3978/api/messages` (for local bot, before ngrok), or ngrok URL.

*   **`FRESHDESK_TO_AZFUNC_SHARED_SECRET`**:
    *   **Description**: A pre-shared secret key that you define. The system simulating the Freshdesk webhook (e.g., Postman/curl) must send this in the `X-Freshdesk-Webhook-Secret` header for the Azure Function to accept the request.
    *   **Source**: You define this secret.
    *   **Example**: `mySuperSecureWebhookSecret123!`

*   **`BOT_APP_ID`** (Azure Function's environment variable):
    *   **Description**: The Microsoft App ID of your Azure Bot. The Azure Function uses this to populate the `recipient.id` field of the Bot Framework Activity it constructs.
    *   **Source**: Azure Bot registration (same as `MicrosoftAppId` for the bot).
    *   **Example**: (GUID, e.g., `abcdef12-3456-7890-abcd-ef1234567890`)

*   **`BOT_NAME`** (Azure Function's environment variable):
    *   **Description**: A display name for your Azure Bot. The Azure Function uses this to populate the `recipient.name` field of the Bot Framework Activity.
    *   **Source**: Your bot's display name.
    *   **Example**: `HelpfulFreshdeskBot`

**`local.settings.json` for Azure Function (Example for Local Development):**
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true", // Or your Azure Storage connection string
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BOT_ENDPOINT_URL": "YOUR_NGROK_URL_OR_BOT_ENDPOINT/api/messages",
    "FRESHDESK_TO_AZFUNC_SHARED_SECRET": "your_chosen_shared_secret",
    "BOT_APP_ID": "your_bot_microsoft_app_id", // Can be blank if bot allows it for local
    "BOT_NAME": "MyTestBot"
  }
}
```
**Important:** Do NOT commit `local.settings.json` with real secrets to source control.
