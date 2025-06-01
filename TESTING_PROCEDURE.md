# End-to-End Freshdesk Integration Testing Procedure

This document outlines the steps to test the communication flow from a simulated Freshdesk message, through an Azure Function intermediary, to the Azure Bot, and the bot's subsequent reply back to Freshdesk, including handover actions.

## Prerequisites

1.  **Azure Bot Project:**
    *   Files: `app.py`, `simple_bot.py`, `freshdesk_client.py`, `config.py`, `requirements.txt` (as implemented).
    *   Python environment with all packages from `requirements.txt` installed (`pip install -r requirements.txt`).
2.  **Azure Function Project:**
    *   Directory: `HttpFreshdeskWebhookTrigger`
    *   Files: `__init__.py`, `function.json`, `requirements.txt`, `host.json`, `sample_freshdesk_payload.json` (as implemented).
    *   Azure Functions Core Tools installed for local execution (`func start`).
    *   Python environment with packages from `HttpFreshdeskWebhookTrigger/requirements.txt` installed.
3.  **ngrok:** Installed and configured to expose local endpoints publicly if testing the bot locally.
4.  **Testing Tool:** A tool like `curl` or Postman to simulate the Freshdesk webhook POST request.
5.  **Configuration:** All necessary environment variables (or values in `config.py` and `local.settings.json`) must be correctly set as detailed in `TESTING_CONFIG.md`.
    *   **Crucially for these tests:**
        *   The Azure Function's `BOT_ENDPOINT_URL` must point to the publicly accessible URL of the running bot (e.g., ngrok URL).
        *   The Azure Function's `FRESHDESK_TO_AZFUNC_SHARED_SECRET` must be known for sending the simulated webhook.
        *   The Bot's Freshdesk configurations in `config.py` (`FRESHDESK_API_KEY`, `FRESHDESK_DOMAIN`, `BOT_FRESHDESK_USER_ID`, `FRESHDESK_BUSINESS_HOUR_ID`, `HANDOVER_GROUP_ID`, `FRESHDESK_PENDING_STATUS_ID`) should be set appropriately for live or mocked testing.

## Testing Steps

**Step 1: Start the Azure Bot**

1.  Navigate to your Azure Bot project directory.
2.  Ensure all configurations in `config.py` (or corresponding environment variables) are set.
3.  Run the bot application:
    ```bash
    python app.py
    ```
4.  The bot should typically start on `http://localhost:3978`.
5.  **If testing locally with an Azure Function that is also local but needs to call a *public* bot endpoint (or if the function is deployed and bot is local):**
    *   Expose the bot's local endpoint using ngrok:
        ```bash
        ngrok http 3978
        ```
    *   Note the public `https://` Forwarding URL provided by ngrok. This will be used as the `BOT_ENDPOINT_URL` for the Azure Function.

**Step 2: Configure and Start the Azure Function**

1.  Navigate to your Azure Function project directory.
2.  Create or update `local.settings.json` with the correct values, especially `BOT_ENDPOINT_URL` and `FRESHDESK_TO_AZFUNC_SHARED_SECRET`.
3.  Run the Azure Function locally:
    ```bash
    func start
    ```
4.  Note the local endpoint for your HTTP trigger (usually `http://localhost:7071/api/HttpFreshdeskWebhookTrigger`).

**Step 3: Simulate Freshdesk Webhook**

1.  Use a tool like `curl` or Postman.
2.  Prepare a POST request to the Azure Function's endpoint noted in Step 2.
3.  **Headers:**
    *   `Content-Type: application/json`
    *   `X-Freshdesk-Webhook-Secret`: The value you set for `FRESHDESK_TO_AZFUNC_SHARED_SECRET`.
4.  **Body:** Use the content of `sample_freshdesk_payload.json`.
    *   To test standard replies, use intents like "TestFreshdesk".
    *   To test handover via intent, use `message_text` like "talk to agent".
    *   To test handover via misunderstanding, send a few unrecognized messages consecutively.
    *Example `curl` command:*
    ```bash
    curl -X POST \
    http://localhost:7071/api/HttpFreshdeskWebhookTrigger \
    -H "Content-Type: application/json" \
    -H "X-Freshdesk-Webhook-Secret: your_chosen_shared_secret" \
    -d @sample_freshdesk_payload.json
    ```

**Step 4: Observe Azure Function Logs**

1.  Check the console where your Azure Function is running.
2.  Logs should indicate:
    *   Processing of the webhook request.
    *   Authentication status.
    *   Forwarding activity to the bot and the outcome.

**Step 5: Observe Azure Bot Logs/Emulator**

1.  Check the console where your Azure Bot is running.
2.  Logs should indicate:
    *   Message reception and CLU processing.
    *   Conversation state changes (e.g., `misunderstanding_count`, `handover_initiated`).
    *   The response sent back to the Azure Function (which then relays to the webhook simulator).
    *   **If Handover is Triggered (when `channel_id` is "freshdesk-webhook"):**
        *   Handover initiation reason.
        *   Business hours check results (live or mocked).
        *   Private note addition attempt and outcome.
        *   Ticket status update attempt and outcome.
        *   The final message constructed for the user, reflecting business hours.
    *   **If a standard Freshdesk reply is triggered (e.g., `TestFreshdesk` intent without handover):**
        *   Log of the reply attempt to Freshdesk.
        *   The `target_ticket_id_for_fd`.
        *   Outcome of the Freshdesk API call.

**Step 6: Verify Freshdesk (If Using Live Credentials and `USE_MOCKED_FRESHDESK` is `False`)**

1.  **For Handover Scenarios (when `channel_id` was "freshdesk-webhook"):**
    *   Open the ticket in Freshdesk corresponding to the `ticket_id` from your `sample_freshdesk_payload.json`.
    *   Verify a **private note** was added. The note should contain the handover reason and a summary of the recent conversation.
    *   Verify the ticket **status** is "Pending" (or the ID configured in `config.FRESHDESK_PENDING_STATUS_ID`).
    *   If `HANDOVER_GROUP_ID` is set in `config.py`, verify the ticket is assigned to this group.
    *   If `HANDOVER_AGENT_ID` is set, verify assignment (this might override group assignment).
2.  **For Standard Reply Scenarios (e.g., `TestFreshdesk` intent without handover):**
    *   Open the target ticket in Freshdesk.
    *   Verify a new **public reply** was added to the ticket by the bot.
    *   The reply should appear as being from the agent whose `BOT_FRESHDESK_USER_ID` is configured.

## Specific Test Cases for Handover Functionality:

1.  **Handover via "RequestAgent" Intent:**
    *   Set `message_text` in `sample_freshdesk_payload.json` to "I want to talk to an agent".
    *   Simulate webhook.
    *   Observe bot logs for `RequestAgent` intent and handover initiation.
    *   Verify Freshdesk actions (note, status, assignment) and user message.
2.  **Handover via Misunderstanding Threshold:**
    *   Send 2 (or `HANDOVER_MISUNDERSTANDING_THRESHOLD`) unrecognized messages via simulated webhooks to the *same ticket ID* (ensure `ticket_id` in payload is consistent for conversation tracking).
    *   Observe bot logs for `misunderstanding_count` incrementing and handover triggering on the last message.
    *   Verify Freshdesk actions and user message.
3.  **Business Hours Check - Within Hours:**
    *   Ensure `FRESHDESK_BUSINESS_HOUR_ID` is set in `config.py` to a valid ID.
    *   Configure the corresponding Freshdesk Business Hours to be *currently open* (or use mock in `freshdesk_client.py` to simulate this).
    *   Trigger a handover.
    *   Verify the user message indicates someone will respond shortly.
4.  **Business Hours Check - Outside Hours:**
    *   Ensure `FRESHDESK_BUSINESS_HOUR_ID` is set.
    *   Configure Freshdesk Business Hours to be *currently closed* (or use mock).
    *   Trigger a handover.
    *   Verify the user message indicates it's outside business hours and there might be a delay.
5.  **Business Hours Check - Configuration Missing/Error:**
    *   Unset `FRESHDESK_BUSINESS_HOUR_ID` or set it to an invalid/placeholder value in `config.py`.
    *   Trigger a handover.
    *   Verify the bot sends a generic handover message that doesn't specify business hours.
6.  **Handover from Emulator/Non-Freshdesk Channel:**
    *   Connect Bot Framework Emulator to the local bot.
    *   Type "talk to an agent".
    *   Verify the bot responds with a message indicating that handover would normally occur in a live Freshdesk channel. No actual Freshdesk API calls for handover should be made.
7.  **Conversation State Reset:**
    *   Trigger handover (e.g., via misunderstanding).
    *   Send another message (intent doesn't matter). Verify the bot does not process it further or gives a "waiting for agent" type message if `conv_state.handover_initiated` is checked early in `on_message_activity`.
    *   (Manual Reset for now) To test again with the same `conversation.id`, you'd need to restart the bot to clear the in-memory `CONVERSATION_STATES` or implement a reset mechanism.

**Troubleshooting:**
*   Check console logs for both the Azure Function and the Azure Bot for any error messages.
*   Verify ngrok is running correctly and the URL is correctly configured in the Azure Function's settings if testing locally.
*   Ensure the `X-Freshdesk-Webhook-Secret` matches between your test tool and the Azure Function's configuration.
*   Double-check all Freshdesk related configurations in `config.py` if doing live tests.
*   Ensure the bot's App Service (if deployed) or local port is not blocked by a firewall.
