# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ChannelAccount

# Import configurations
import config

# Import Freshdesk client
from freshdesk_client import (
    send_reply_to_freshdesk,
    get_freshdesk_business_hours,
    is_within_business_hours,
    add_private_note_to_ticket,
    update_ticket_status
)

# Import Salesforce client (if used for other intents)
from salesforce_client import authenticate_salesforce, get_contact_by_email, get_recent_cases_for_contact

# Import Snowflake client
from snowflake_client import get_knowledge_answer # Assuming connect_snowflake is handled within get_knowledge_answer or a global conn

import asyncio
import re # For parsing snowflake kb command
from typing import Dict, Any

# --- Conversation State ---
class ConversationState:
    def __init__(self):
        self.misunderstanding_count = 0
        self.user_interaction_history = [] # To store (user_message, bot_response) tuples
        self.handover_initiated = False # Flag to prevent multiple handovers in a short span

    def add_interaction(self, user_message: str, bot_response: str):
        self.user_interaction_history.append(f"User: {user_message}\nBot: {bot_response}")
        if len(self.user_interaction_history) > 5: # Keep last 5 interactions
            self.user_interaction_history.pop(0)

    def get_interaction_summary(self) -> str:
        return "\n---\n".join(self.user_interaction_history)

class SimpleBot(ActivityHandler):
    """
    This bot handles incoming messages, uses a (mocked) CLU service
    to determine intent, attempts Salesforce data retrieval, queries Snowflake KB,
    and for specific intents, sends a message to Freshdesk or initiates handover.
    """

    # In-memory dictionary to store conversation states.
    # In a production bot, you'd use UserState and ConversationState from botbuilder.core.
    CONVERSATION_STATES: Dict[str, ConversationState] = {}
    HANDOVER_MISUNDERSTANDING_THRESHOLD = 2 # Number of misunderstandings before handover

    def _get_conversation_state(self, conversation_id: str) -> ConversationState:
        """Gets or creates the state for a conversation."""
        if conversation_id not in self.CONVERSATION_STATES:
            self.CONVERSATION_STATES[conversation_id] = ConversationState()
        return self.CONVERSATION_STATES[conversation_id]

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(f"Hello {member.name}! Welcome. Try 'order status', 'talk to agent', 'test freshdesk', 'salesforce lookup', or 'snowflake kb category: your_category keywords: your_keywords'.")
                )

    async def on_message_activity(self, turn_context: TurnContext):
        user_message = turn_context.activity.text
        incoming_activity: Activity = turn_context.activity
        conversation_id = turn_context.activity.conversation.id
        conv_state = self._get_conversation_state(conversation_id)

        response_text = ""

        # If handover has been initiated, the bot should ideally stay quiet or provide minimal responses
        # until a human agent takes over or the state is reset.
        if conv_state.handover_initiated:
            # response_text = "Our support team has been notified. Please wait for assistance."
            # await turn_context.send_activity(MessageFactory.text(response_text))
            # conv_state.add_interaction(user_message, response_text) # Optionally log this interaction
            return # Don't process further if handover is active for this conversation

        # --- Salesforce Data Retrieval Logic ---
        if "salesforce lookup" in user_message.lower():
            logging.info("Attempting Salesforce data retrieval...")
            auth_success = await authenticate_salesforce()
            salesforce_info = ""
            if auth_success:
                salesforce_info += "Salesforce: Authenticated (or mock).\n"
                salesforce_test_email = "test@example.com"
                contact = await get_contact_by_email(salesforce_test_email)
                if contact:
                    contact_id = contact.get("Id")
                    contact_name = contact.get("Name")
                    salesforce_info += f"Salesforce: Contact found: {contact_name} (ID: {contact_id}).\n"
                    if contact_id:
                        cases = await get_recent_cases_for_contact(contact_id)
                        if cases is not None:
                            salesforce_info += f"Salesforce: Found {len(cases)} recent case(s) for {contact_name}:\n"
                            for case in cases:
                                salesforce_info += f"  - Case #{case.get('CaseNumber')}: {case.get('Subject')} (Status: {case.get('Status')})\n"
                        else:
                            salesforce_info += "Salesforce: Failed to retrieve cases or no cases found.\n"
                else:
                    salesforce_info += f"Salesforce: No contact found for email: {salesforce_test_email}.\n"
            else:
                salesforce_info += "Salesforce: Authentication failed. Cannot retrieve data.\n"

            response_text = salesforce_info if salesforce_info else "No Salesforce info to display."
            await turn_context.send_activity(MessageFactory.text(response_text))
            conv_state.add_interaction(user_message, response_text)
            return

        # --- Snowflake Knowledge Base Query Logic ---
        if user_message.lower().startswith("snowflake kb"):
            logging.info("Attempting Snowflake KB query...")
            snowflake_kb_info = ""
            match = re.search(r"category:\s*(.*?)\s*keywords:\s*(.*)", user_message, re.IGNORECASE)
            if match:
                category, keywords = match.groups()
                category = category.strip()
                keywords = keywords.strip()
                if category and keywords:
                    snowflake_kb_info += f"Snowflake KB: Searching in category '{category}' for keywords '{keywords}'.\n"
                    answer = await get_knowledge_answer(category, keywords)
                    if answer:
                        snowflake_kb_info += f"Snowflake KB Answer: {answer}\n"
                    else:
                        snowflake_kb_info += "Snowflake KB: No answer found or query failed.\n"
                    if config.USE_MOCKED_SNOWFLAKE:
                        snowflake_kb_info += "(Note: Snowflake KB call was MOCKED as per configuration)\n"
                else:
                    snowflake_kb_info += "Snowflake KB: Please provide category and keywords in the format 'snowflake kb category: your_category keywords: your_keywords'.\n"
            else:
                snowflake_kb_info += "Snowflake KB: Invalid command format. Use 'snowflake kb category: <category> keywords: <keywords>'.\n"

            response_text = snowflake_kb_info
            await turn_context.send_activity(MessageFactory.text(response_text))
            conv_state.add_interaction(user_message, response_text)
            return

        # --- (Mocked) CLU Intent Recognition & Existing/New Freshdesk Logic ---
        clu_result = self._mock_clu_recognizer(user_message)
        top_intent = clu_result.get("result", {}).get("prediction", {}).get("topIntent", "None")
        confidence = clu_result.get("result", {}).get("prediction", {}).get("intents", [{}])[0].get("confidenceScore", 0.0)

        logging.info(f"User message: '{user_message}', CLU Top Intent: {top_intent}, Confidence: {confidence}")

        initiate_handover = False
        handover_reason = ""

        if top_intent == "RequestAgent":
            initiate_handover = True
            handover_reason = "User explicitly requested an agent."
            response_text = "Okay, I'll get a human agent to assist you." # Initial response before handover process
        elif top_intent == "None" or confidence < 0.5: # Example confidence threshold
            conv_state.misunderstanding_count += 1
            handover_reason = f"Bot reached misunderstanding threshold ({conv_state.misunderstanding_count}/{self.HANDOVER_MISUNDERSTANDING_THRESHOLD})."
            response_text = "I'm having trouble understanding. "
            if conv_state.misunderstanding_count >= self.HANDOVER_MISUNDERSTANDING_THRESHOLD:
                initiate_handover = True
                response_text += "Let me get a human to help."
            else:
                response_text += "Could you please rephrase?"
        else: # Valid intent understood, reset counter
            conv_state.misunderstanding_count = 0
            # Handle other intents as before
            if top_intent == "Greeting":
                response_text = "Hello! How can I help you today?"
            elif top_intent == "Goodbye":
                response_text = "Goodbye! Have a great day."
            elif top_intent == "GetOrderStatus" or top_intent == "TestFreshdesk":
                # This part remains similar to existing logic for these intents,
                # but we'll separate the Freshdesk communication for clarity if not handover.
                # For now, let's assume these intents don't auto-trigger handover unless they fail repeatedly.
                response_text = f"Okay, processing your '{top_intent}' request."
                # Potentially add specific Freshdesk interaction here if not a handover
                if top_intent == "TestFreshdesk":
                    # This specific logic for TestFreshdesk can be kept or refactored
                    # For now, let's keep it simple for the handover focus
                    target_ticket_id_for_fd = config.TEST_FRESHDESK_TICKET_ID
                    message_to_freshdesk = f"Bot received intent: {top_intent}. User message: '{user_message}'."
                    await send_reply_to_freshdesk(target_ticket_id_for_fd, message_to_freshdesk, config.BOT_FRESHDESK_USER_ID)
                    response_text += f" Logged to test ticket {target_ticket_id_for_fd}."

            else: # Fallback for other recognized intents not explicitly handled for handover
                response_text = f"I understand you want to '{top_intent}'. How can I assist with that specifically?"

        # --- Handover Logic ---
        if initiate_handover and incoming_activity.channel_id == "freshdesk-webhook":
            conv_state.handover_initiated = True # Set flag
            target_ticket_id_str = incoming_activity.conversation.id
            try:
                target_ticket_id = int(target_ticket_id_str)
                logging.info(f"Handover initiated for ticket {target_ticket_id}. Reason: {handover_reason}")

                # 1. Get Business Hours
                business_hours_data = None
                if config.FRESHDESK_BUSINESS_HOUR_ID and config.FRESHDESK_BUSINESS_HOUR_ID != "YOUR_FRESHDESK_BUSINESS_HOUR_ID_PLACEHOLDER":
                    business_hours_data = await get_freshdesk_business_hours(config.FRESHDESK_BUSINESS_HOUR_ID)

                is_open = False # Default to closed if BH ID not set or call fails
                if business_hours_data:
                    is_open_check = is_within_business_hours(business_hours_data)
                    if is_open_check is not None:
                        is_open = is_open_check
                    else: # Error during check
                         response_text += "\nCould not reliably determine business hours."
                else:
                    response_text += "\nBusiness hours configuration not found or mock mode."


                # 2. Add Private Note
                note_content = f"User handover initiated by bot.\nReason: {handover_reason}\nInteraction Summary:\n{conv_state.get_interaction_summary()}\nUser's last message: {user_message}"
                await add_private_note_to_ticket(target_ticket_id, note_content)

                # 3. Update Ticket Status (and optionally assign)
                await update_ticket_status(
                    ticket_id=target_ticket_id,
                    status_id=config.FRESHDESK_PENDING_STATUS_ID,
                    # responder_id=config.HANDOVER_AGENT_ID, # Uncomment to assign to specific agent
                    group_id=config.HANDOVER_GROUP_ID # Assign to default group if configured
                )

                # 4. Inform User
                if is_open:
                    response_text = f"I've flagged this for our support team. Someone will get back to you shortly on this ticket ({target_ticket_id})."
                else:
                    response_text = f"I've flagged this for our support team. Please note it's currently outside our business hours, so there might be a delay. Someone will respond to ticket ({target_ticket_id}) as soon as possible."

                conv_state.misunderstanding_count = 0 # Reset counter after successful handover

            except ValueError:
                logging.error(f"Error: Handover - Conversation ID '{target_ticket_id_str}' from Freshdesk webhook is not a simple integer.")
                response_text = "There was an issue processing the handover, the ticket ID is invalid."
            except Exception as e:
                logging.error(f"Error during handover process: {e}")
                response_text = "An error occurred while trying to hand over to an agent. Please try again later."

        elif initiate_handover and incoming_activity.channel_id != "freshdesk-webhook":
            # Handle handover request from other channels (e.g., emulator)
            conv_state.handover_initiated = True # Set flag, though actions might be limited
            response_text = "You've requested an agent. In a live Freshdesk channel, this would create/update a ticket and notify our team. For now, please contact support directly through our official channels."
            conv_state.misunderstanding_count = 0

        # Send the determined response
        if response_text:
            await turn_context.send_activity(MessageFactory.text(response_text))

        # Log interaction (after sending response, so bot's response is captured)
        conv_state.add_interaction(user_message, response_text if response_text else "(No explicit bot response sent this turn)")


    def _mock_clu_recognizer(self, text: str):
        text = text.lower()
        intent = "None"
        confidence_score = 0.1

        if "hello" in text or "hi" in text or "hey" in text:
            intent = "Greeting"
            confidence_score = 0.95
        elif "bye" in text or "see you" in text or "good bye" in text:
            intent = "Goodbye"
            confidence_score = 0.93
        elif "order status" in text or "where is my order" in text or "track order" in text:
            intent = "GetOrderStatus"
            confidence_score = 0.85
        elif "agent" in text or "human" in text or "talk to someone" in text:
            intent = "RequestAgent"
            confidence_score = 0.80
        elif "test freshdesk" in text or "freshdesk test" in text:
            intent = "TestFreshdesk"
            confidence_score = 0.99
        # Note: "salesforce lookup" and "snowflake kb" are handled by direct string checks for now, not CLU intents.

        mock_response = {
            "kind": "ConversationResult",
            "result": {
                "query": text,
                "prediction": {
                    "topIntent": intent,
                    "projectKind": "Conversation",
                    "intents": [
                        {
                            "category": intent,
                            "confidenceScore": confidence_score
                        }
                    ],
                    "entities": []
                }
            }
        }
        return mock_response

    async def _call_clu_service(self, text: str):
        # (Conceptual real CLU call - not used by current mocked implementation)
        try:
            clu_client = ConversationAnalysisClient(config.CLU_ENDPOINT, AzureKeyCredential(config.CLU_KEY))
            clu_request = {
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": { "id": "1", "participantId": "user", "text": text }
                },
                "parameters": {
                    "projectName": config.CLU_PROJECT_NAME,
                    "deploymentName": config.CLU_DEPLOYMENT_NAME,
                    "stringIndexType": "TextElement_V8",
                }
            }
            # This would need to be truly async in a production bot:
            # loop = asyncio.get_event_loop()
            # response = await loop.run_in_executor(None, lambda: clu_client.analyze_conversation(clu_request))
            response = clu_client.analyze_conversation(clu_request) # Placeholder for actual async call

            prediction = response.get("result", {}).get("prediction", {})
            return prediction
        except Exception as e:
            print(f"Error calling CLU service: {e}")
            return {"topIntent": "None", "entities": []}

```
**Key changes in `simple_bot.py`:**
*   Imported `get_knowledge_answer` from `snowflake_client.py` and `re` for parsing.
*   In `on_message_activity`:
    *   Added a check for messages starting with "snowflake kb".
    *   If matched, it parses out `category` and `keywords` using regex.
    *   Calls `await get_knowledge_answer(category, keywords)`.
    *   Sends the result (or a "not found" / "mocked" message) back to the user.
    *   This Snowflake logic is placed before the CLU intent processing for this demonstration, and the turn ends after handling the Snowflake query.
*   Updated the welcome message to include the new "snowflake kb" command.

The example mocked JSON for a knowledge base query is already defined within `snowflake_client.py` in `MOCK_KB_ANSWER` and `MOCK_NO_KB_ANSWER_FOUND`.

The final step is to create the `SNOWFLAKE_CONFIG.md` file.
