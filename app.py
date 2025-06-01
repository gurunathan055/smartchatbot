# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import asyncio
from aiohttp import web
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext
)
from botbuilder.schema import Activity, ActivityTypes

from simple_bot import SimpleBot # Import the bot logic

# --- Bot Configuration (Conceptual - Replace with your actual values if needed for deployment) ---
# These are typically obtained from your bot registration in Azure.
# For local testing, these can often be left blank if your emulator doesn't require them,
# or you use the values provided by tools like ngrok when tunneling.
APP_ID = ""  # Your Microsoft App ID (Leave blank for local testing if not set up)
APP_PASSWORD = "" # Your Microsoft App Password (Leave blank for local testing if not set up)
# --- End Bot Configuration ---

# Create adapter settings
SETTINGS = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)

# Create adapter
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create the bot instance
BOT = SimpleBot()

# Listen for incoming requests on /api/messages
async def messages(req: web.Request) -> web.Response:
    """
    Main bot message handler.
    """
    if "application/json" in req.headers.get("Content-Type", ""):
        body = await req.json()
    else:
        return web.Response(status=415) # Unsupported Media Type

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        if response:
            return web.json_response(response.body, status=response.status)
        return web.Response(status=201) # Accepted
    except Exception as exception:
        print(f"Error processing activity: {exception}")
        # You might want to log the full exception details in a real application
        # import traceback
        # print(traceback.format_exc())
        return web.Response(status=500, text=str(exception))

# Create the aiohttp web application
APP = web.Application()
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        print("Bot is starting. Open Bot Framework Emulator and connect to http://localhost:3978/api/messages")
        web.run_app(APP, host="localhost", port=3978)
    except Exception as e:
        raise e
