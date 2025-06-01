import aiohttp
import base64
import json
import config # Import configuration
import datetime
import pytz # For timezone handling


# --- Helper for Authentication ---
def _get_auth_headers():
    """Helper function to generate Freshdesk authentication headers."""
    auth_string = f"{config.FRESHDESK_API_KEY}:X"  # 'X' can be used as a dummy password
    encoded_auth_string = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth_string}"
    }

async def send_reply_to_freshdesk(ticket_id: int, message_body: str, bot_user_id: int) -> bool:
    """
    Sends a reply message to a specific Freshdesk ticket.

    Args:
        ticket_id: The ID of the Freshdesk ticket.
        message_body: The content of the message to send.
        bot_user_id: The Freshdesk user ID of the agent making the reply (representing the bot).

    Returns:
        True if the message was sent successfully (or mocked successfully), False otherwise.
    """
    if config.USE_MOCKED_FRESHDESK or not isinstance(bot_user_id, int):
        print(f"[MOCKED] Freshdesk API Call: Would send reply to ticket {ticket_id} with body: '{message_body}' as user {bot_user_id}")
        # Simulate success for mocked call
        return True

    url = f"https://{config.FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/reply"

    payload = {
        "body": message_body,
        "user_id": bot_user_id  # ID of the agent posting the reply
    }

    headers = _get_auth_headers()

    print(f"Attempting to send reply to Freshdesk ticket {ticket_id} at URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Headers: User-Agent, Accept, Accept-Encoding, Authorization") # Don't log full auth header

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                if 200 <= response.status < 300:
                    print(f"Successfully sent reply to Freshdesk ticket {ticket_id}. Status: {response.status}")
                    # print(f"Freshdesk Response: {response_text}") # Can be verbose
                    return True
                else:
                    print(f"Failed to send reply to Freshdesk ticket {ticket_id}. Status: {response.status}, Response: {response_text}")
                    return False
    except aiohttp.ClientConnectorError as e:
        print(f"Connection Error sending reply to Freshdesk: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while sending reply to Freshdesk: {e}")
        return False

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    # Ensure you have set your environment variables for config.py to pick them up
    # or that USE_MOCKED_FRESHDESK is True in config.py

    async def main():
        if config.USE_MOCKED_FRESHDESK:
            print("Running Freshdesk client in MOCKED mode.")
        else:
            print("Running Freshdesk client in LIVE mode (ensure credentials are set).")

        ticket_id_to_test = config.TEST_FRESHDESK_TICKET_ID
        bot_agent_id = config.BOT_FRESHDESK_USER_ID

        if not isinstance(bot_agent_id, int):
             print(f"Error: BOT_FRESHDESK_USER_ID ('{bot_agent_id}') is not a valid integer. Please check your configuration.")
             print("Switching to MOCKED mode for this test run if not already.")
             config.USE_MOCKED_FRESHDESK = True


        success = await send_reply_to_freshdesk(
            ticket_id=ticket_id_to_test,
            message_body="Hello from the Azure Bot! This is a test reply via API.",
            bot_user_id=bot_agent_id if isinstance(bot_agent_id, int) else 0 # Pass 0 if invalid for mock
        )
        if success:
            print("Test reply sent (or mocked) successfully.")
        else:
            print("Test reply failed.")

    asyncio.run(main())


async def get_freshdesk_business_hours(business_hour_id: str) -> dict | None:
    """
    Retrieves business hours configuration from Freshdesk.

    Args:
        business_hour_id: The ID of the business hour configuration in Freshdesk.

    Returns:
        A dictionary containing the business hours data if successful, None otherwise.
        Example successful return:
        {
            "time_zone": "America/New_York",
            "business_hours": {
                "monday": {"start_time": "09:00:00", "end_time": "17:00:00"},
                ...
            }
        }
        (Note: API returns times like "08:00:00 am", this will be parsed later)
    """
    if config.USE_MOCKED_FRESHDESK or not business_hour_id or business_hour_id == "YOUR_FRESHDESK_BUSINESS_HOUR_ID_PLACEHOLDER":
        print(f"[MOCKED] Freshdesk API Call: Would get business hours for ID {business_hour_id}")
        # Return a default "always open" mock for testing if needed, or specific hours
        return {
            "time_zone": "UTC", # Or a specific test timezone like "America/New_York"
            "business_hours": {
                "monday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"},
                "tuesday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"},
                "wednesday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"},
                "thursday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"},
                "friday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"},
                "saturday": {"start_time": "00:00:00 am", "end_time": "11:59:59 pm"}, # Closed example
                "sunday": None # Explicitly closed example
            }
        }

    url = f"https://{config.FRESHDESK_DOMAIN}/api/v2/business_hours/{business_hour_id}"
    headers = _get_auth_headers()

    print(f"Attempting to get Freshdesk business hours for ID {business_hour_id} at URL: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response_text = await response.text()
                if response.status == 200:
                    data = json.loads(response_text)
                    print(f"Successfully retrieved business hours for ID {business_hour_id}.")
                    return data # Contains 'time_zone' and 'business_hours' map
                else:
                    print(f"Failed to get business hours for ID {business_hour_id}. Status: {response.status}, Response: {response_text}")
                    return None
    except aiohttp.ClientConnectorError as e:
        print(f"Connection Error getting business hours: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while getting business hours: {e}")
        return None

def is_within_business_hours(business_hours_data: dict | None) -> bool | None:
    """
    Checks if the current time is within the provided Freshdesk business hours.

    Args:
        business_hours_data: A dictionary containing 'time_zone' and 'business_hours'
                             (e.g., from get_freshdesk_business_hours).

    Returns:
        True if within business hours, False if outside, None if data is invalid or check fails.
    """
    if not business_hours_data or "time_zone" not in business_hours_data or "business_hours" not in business_hours_data:
        print("Invalid business hours data provided.")
        return None

    try:
        fd_timezone_str = business_hours_data["time_zone"]
        # Normalize common timezone representations if necessary (e.g. from Windows to IANA)
        # For now, assuming Freshdesk provides IANA standard timezones.
        fd_timezone = pytz.timezone(fd_timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Unknown timezone provided by Freshdesk: {fd_timezone_str}")
        return None # Cannot determine if timezone is invalid

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_local_fd = now_utc.astimezone(fd_timezone)

    current_day_name = now_local_fd.strftime('%A').lower() # Monday, Tuesday, etc.
    current_time_obj = now_local_fd.time()

    day_schedule = business_hours_data["business_hours"].get(current_day_name)

    if day_schedule is None: # Typically means closed on this day
        print(f"Day '{current_day_name}' not in business hours schedule or explicitly None (Closed).")
        return False

    start_time_str = day_schedule.get("start_time") # e.g., "09:00:00 am"
    end_time_str = day_schedule.get("end_time")     # e.g., "05:00:00 pm"

    if not start_time_str or not end_time_str:
        print(f"Missing start or end time for '{current_day_name}'.")
        return False # Treat as closed if schedule is incomplete

    try:
        # Freshdesk times are like "08:00:00 am" or "11:59:59 pm"
        # Python's strptime can parse AM/PM.
        start_time_obj = datetime.datetime.strptime(start_time_str, "%I:%M:%S %p").time()
        end_time_obj = datetime.datetime.strptime(end_time_str, "%I:%M:%S %p").time()
    except ValueError as e:
        print(f"Error parsing start/end time from Freshdesk data: {e}")
        # Fallback for 24-hour format if AM/PM fails or is missing, common in some API outputs
        try:
            start_time_obj = datetime.datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time_obj = datetime.datetime.strptime(end_time_str, "%H:%M:%S").time()
        except ValueError as e_24:
             print(f"Error parsing start/end time (24h format) from Freshdesk data: {e_24}")
             return None # Cannot parse times

    print(f"Current Freshdesk local time: {now_local_fd.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    print(f"Checking against schedule for {current_day_name}: {start_time_obj} - {end_time_obj}")

    # Handle cases where end_time might be "11:59:59 pm" or similar for full day coverage
    # If end_time is effectively midnight (e.g., 23:59:59), it means "until end of day"
    if end_time_obj == datetime.time(23, 59, 59):
        return start_time_obj <= current_time_obj

    return start_time_obj <= current_time_obj < end_time_obj


async def add_private_note_to_ticket(ticket_id: int, note_body: str) -> bool:
    """
    Adds a private note to a specific Freshdesk ticket.

    Args:
        ticket_id: The ID of the Freshdesk ticket.
        note_body: The content of the private note.

    Returns:
        True if the note was added successfully, False otherwise.
    """
    if config.USE_MOCKED_FRESHDESK:
        print(f"[MOCKED] Freshdesk API Call: Would add private note to ticket {ticket_id}: '{note_body}'")
        return True

    url = f"https://{config.FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/notes"
    payload = {
        "body": note_body,
        "private": True
    }
    headers = _get_auth_headers()

    print(f"Attempting to add private note to Freshdesk ticket {ticket_id} at URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                if 200 <= response.status < 300:
                    print(f"Successfully added private note to ticket {ticket_id}. Status: {response.status}")
                    return True
                else:
                    print(f"Failed to add private note to ticket {ticket_id}. Status: {response.status}, Response: {response_text}")
                    return False
    except aiohttp.ClientConnectorError as e:
        print(f"Connection Error adding private note: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while adding private note: {e}")
        return False

async def update_ticket_status(ticket_id: int, status_id: int, responder_id: int = None, group_id: int = None) -> bool:
    """
    Updates the status and optionally assigns a Freshdesk ticket.

    Args:
        ticket_id: The ID of the Freshdesk ticket.
        status_id: The numerical ID for the new status.
        responder_id: Optional. The agent ID to assign the ticket to.
        group_id: Optional. The group ID to assign the ticket to.

    Returns:
        True if the ticket was updated successfully, False otherwise.
    """
    if config.USE_MOCKED_FRESHDESK:
        mock_payload = {"status": status_id}
        if responder_id:
            mock_payload["responder_id"] = responder_id
        if group_id:
            mock_payload["group_id"] = group_id
        print(f"[MOCKED] Freshdesk API Call: Would update ticket {ticket_id} with payload: {json.dumps(mock_payload)}")
        return True

    url = f"https://{config.FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"

    payload = {"status": status_id}
    if responder_id is not None:
        payload["responder_id"] = responder_id
    if group_id is not None:
        payload["group_id"] = group_id

    headers = _get_auth_headers()

    print(f"Attempting to update Freshdesk ticket {ticket_id} at URL: {url} with payload: {json.dumps(payload)}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                if 200 <= response.status < 300:
                    print(f"Successfully updated ticket {ticket_id}. Status: {response.status}")
                    return True
                else:
                    print(f"Failed to update ticket {ticket_id}. Status: {response.status}, Response: {response_text}")
                    return False
    except aiohttp.ClientConnectorError as e:
        print(f"Connection Error updating ticket: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while updating ticket: {e}")
        return False
