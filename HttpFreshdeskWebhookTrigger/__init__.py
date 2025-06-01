import logging
import json
import os
import uuid
import datetime
import aiohttp
import azure.functions as func

# --- Configuration (Load from Environment Variables) ---
BOT_ENDPOINT_URL = os.environ.get("BOT_ENDPOINT_URL")
# Example: "http://your-bot-app-service.azurewebsites.net/api/messages"
# For local testing with ngrok: "http://<your_ngrok_subdomain>.ngrok.io/api/messages"

SHARED_SECRET = os.environ.get("FRESHDESK_TO_AZFUNC_SHARED_SECRET")
# A secret you define and also configure in Freshdesk's webhook setup (or simulator)

BOT_APP_ID = os.environ.get("BOT_APP_ID", "") # Microsoft App ID of your Azure Bot
BOT_NAME = os.environ.get("BOT_NAME", "MyAzureBot") # A display name for your bot

# --- End Configuration ---

def get_utc_timestamp():
    """Returns the current UTC timestamp in ISO 8601 format suitable for Bot Framework."""
    return datetime.datetime.utcnow().isoformat() + "Z"

async def forward_activity_to_bot(activity: dict):
    """
    Forwards the constructed Bot Framework Activity to the bot's messaging endpoint.
    """
    if not BOT_ENDPOINT_URL:
        logging.error("BOT_ENDPOINT_URL is not configured.")
        return False

    logging.info(f"Forwarding activity to bot at: {BOT_ENDPOINT_URL}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(BOT_ENDPOINT_URL, json=activity) as response:
                if 200 <= response.status < 300:
                    logging.info(f"Successfully forwarded activity to bot. Status: {response.status}")
                    return True
                else:
                    response_text = await response.text()
                    logging.error(
                        f"Failed to forward activity to bot. Status: {response.status}, Response: {response_text}"
                    )
                    return False
    except aiohttp.ClientConnectorError as e:
        logging.error(f"Connection error forwarding activity to bot: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while forwarding activity: {e}")
        return False

def transform_freshdesk_to_activity(freshdesk_payload: dict) -> dict:
    """
    Transforms a (simulated) Freshdesk webhook payload into a Bot Framework Activity.
    """
    ticket_id = freshdesk_payload.get("ticket_id")
    sender_id = freshdesk_payload.get("message_sender_id")
    sender_name = freshdesk_payload.get("message_sender_name", "Freshdesk User")
    message_text = freshdesk_payload.get("message_text")
    # ticket_subject = freshdesk_payload.get("ticket_subject", "") # Optional

    if not all([ticket_id, sender_id, message_text]):
        logging.error("Freshdesk payload is missing required fields (ticket_id, message_sender_id, message_text).")
        return None

    activity_id = str(uuid.uuid4())
    timestamp = get_utc_timestamp()

    # The serviceUrl for an activity injected this way might need careful consideration.
    # For the bot to reply back through the same channel (Freshdesk via this function),
    # this function would need to expose an endpoint for the bot to call,
    # and that endpoint URL would be the serviceUrl.
    # For simplicity in this one-way (Freshdesk-to-Bot) example, we use a placeholder
    # or the function's own invocation URL if that were relevant for direct replies.
    # However, the Azure Bot typically expects the serviceUrl to be that of the channel connector.
    # If the bot is expected to reply via Freshdesk API directly (as in previous subtask),
    # this serviceUrl might be less critical for the reply path but important for protocol adherence.
    # Using a conceptual service URL.
    service_url = f"https://{os.environ.get('WEBSITE_HOSTNAME', 'freshdesk-intermediary.azurewebsites.net')}/api/messages"


    activity = {
        "type": "message",
        "id": activity_id,
        "timestamp": timestamp,
        "serviceUrl": service_url, # See comment above
        "channelId": "freshdesk-webhook", # Custom channel ID
        "from": { # Renamed from 'from_property' for consistency with Bot Framework SDK naming
            "id": str(sender_id), # Ensure ID is a string
            "name": sender_name,
            "role": "user"
        },
        "recipient": { # Represents the bot
            "id": BOT_APP_ID,
            "name": BOT_NAME,
            "role": "bot"
        },
        "text": message_text,
        "conversation": {
            "id": str(ticket_id), # Use Freshdesk ticket ID as conversation ID
            "isGroup": False, # Assuming 1-on-1 with bot for now
            "conversationType": "freshdesk_ticket",
            # "tenantId": If applicable
        },
        "channelData": { # Optional: include the raw Freshdesk payload
            "source": "freshdesk",
            "freshdeskPayload": freshdesk_payload
        }
    }
    return activity

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a Freshdesk webhook request.')

    # 1. Request Validation (Shared Secret)
    incoming_secret = req.headers.get("X-Freshdesk-Webhook-Secret")
    if not SHARED_SECRET:
        logging.error("SHARED_SECRET is not configured in Azure Function settings.")
        return func.HttpResponse(
             "Webhook secret not configured on server.",
             status_code=500
        )
    if incoming_secret != SHARED_SECRET:
        logging.warning("Unauthorized attempt: Shared secret mismatch or not provided.")
        return func.HttpResponse(
             "Unauthorized: Invalid or missing shared secret.",
             status_code=401 # Or 403 Forbidden
        )

    # 2. Get Request Body (Simulated Freshdesk Payload)
    try:
        req_body = req.get_json()
    except ValueError:
        logging.error("Invalid JSON in request body.")
        return func.HttpResponse(
             "Please pass a valid JSON object in the request body",
             status_code=400
        )

    logging.info(f"Received Freshdesk payload: {req_body}")

    # 3. Transform Freshdesk Payload to Bot Framework Activity
    bot_activity = transform_freshdesk_to_activity(req_body)
    if not bot_activity:
        return func.HttpResponse(
             "Failed to transform Freshdesk payload due to missing required fields.",
             status_code=400
        )

    # 4. Forward Activity to Bot
    success = await forward_activity_to_bot(bot_activity)

    if success:
        logging.info("Successfully forwarded activity to bot.")
        return func.HttpResponse(
                 "Message successfully forwarded to bot.",
                 status_code=200
            )
    else:
        logging.error("Failed to forward activity to bot.")
        return func.HttpResponse(
                 "Error forwarding message to bot.",
                 status_code=500
            )

# --- Sample Freshdesk Payload (for testing and reference) ---
# This would be part of the documentation, not typically in the function code itself.
# {
#   "ticket_id": 789,
#   "message_sender_id": "user_freshdesk_123",
#   "message_sender_name": "Jane Doe",
#   "message_text": "Hello, I need an update on my order.",
#   "ticket_subject": "Order Inquiry #XYZ123"
# }
# --- End Sample ---
