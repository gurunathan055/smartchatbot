import logging
import aiohttp
import json
from urllib.parse import urlencode
import config # Import configuration

# --- Mocked Salesforce Data ---
MOCK_CONTACT_BY_EMAIL = {
    "totalSize": 1,
    "done": True,
    "records": [
        {
            "attributes": {"type": "Contact", "url": "/services/data/v58.0/sobjects/Contact/003xx000003EXAMPLE"},
            "Id": "003xx000003EXAMPLE",
            "Name": "John Doe (Mocked)",
            "Email": "test@example.com",
            "Phone": "123-456-7890"
        }
    ]
}

MOCK_CASES_BY_CONTACT_ID = {
    "totalSize": 2,
    "done": True,
    "records": [
        {
            "attributes": {"type": "Case", "url": "/services/data/v58.0/sobjects/Case/500xx000001EXAMPLE"},
            "CaseNumber": "00001001",
            "Subject": "Mocked Case 1: Cannot login",
            "Status": "New",
            "CreatedDate": "2023-10-26T10:00:00.000+0000"
        },
        {
            "attributes": {"type": "Case", "url": "/services/data/v58.0/sobjects/Case/500xx000002EXAMPLE"},
            "CaseNumber": "00001002",
            "Subject": "Mocked Case 2: Product defect",
            "Status": "Working",
            "CreatedDate": "2023-10-27T11:30:00.000+0000"
        }
    ]
}

MOCK_NO_RECORDS_FOUND = {"totalSize": 0, "done": True, "records": []}

# --- End Mocked Salesforce Data ---

# Globals to store auth details (simplified for this example)
# In a production scenario, manage tokens more robustly (e.g., in a class instance, secure storage, refresh mechanisms)
_access_token = None
_instance_url = None
SALESFORCE_API_VERSION = "v58.0" # Specify a recent API version

async def authenticate_salesforce():
    """
    Authenticates with Salesforce using OAuth 2.0 Username-Password flow (or mocks it).
    Stores access_token and instance_url globally for subsequent calls.
    Returns:
        bool: True if authentication was successful or mocked, False otherwise.
    """
    global _access_token, _instance_url

    if _access_token and _instance_url: # Already authenticated
        logging.info("Salesforce: Already authenticated.")
        return True

    if config.USE_MOCKED_SALESFORCE:
        _access_token = "MOCK_ACCESS_TOKEN_12345"
        _instance_url = "https://your_mocked_instance.my.salesforce.com"
        logging.info(f"Salesforce: Using MOCKED authentication. Token: {_access_token}, Instance URL: {_instance_url}")
        return True

    token_url = f"{config.SALESFORCE_LOGIN_URL}/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": config.SALESFORCE_CLIENT_ID,
        "client_secret": config.SALESFORCE_CLIENT_SECRET,
        "username": config.SALESFORCE_USERNAME,
        "password": config.SALESFORCE_PASSWORD,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    logging.info(f"Salesforce: Attempting authentication to {token_url} with user {config.SALESFORCE_USERNAME}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=payload, headers=headers) as response:
                response_data = await response.json()
                if response.status == 200 and "access_token" in response_data:
                    _access_token = response_data["access_token"]
                    _instance_url = response_data["instance_url"]
                    logging.info(f"Salesforce: Authentication successful. Instance URL: {_instance_url}")
                    # Do not log the access token itself for security reasons
                    return True
                else:
                    logging.error(f"Salesforce: Authentication failed. Status: {response.status}, Response: {response_data}")
                    _access_token = None
                    _instance_url = None
                    return False
    except aiohttp.ClientConnectorError as e:
        logging.error(f"Salesforce: Connection error during authentication: {e}")
        return False
    except Exception as e:
        logging.error(f"Salesforce: Unexpected error during authentication: {e}")
        return False

async def query_salesforce(soql_query: str) -> dict:
    """
    Executes a SOQL query against Salesforce (or mocks it).
    Requires prior successful authentication.

    Args:
        soql_query: The SOQL query string.

    Returns:
        A dictionary representing the JSON response from Salesforce, or a mock dictionary.
        Returns None if authentication fails or an error occurs.
    """
    global _access_token, _instance_url

    if not (_access_token and _instance_url):
        logging.warning("Salesforce: Not authenticated. Attempting authentication first.")
        if not await authenticate_salesforce():
            logging.error("Salesforce: Authentication required for query but failed.")
            return None # Or raise an exception

    if config.USE_MOCKED_SALESFORCE:
        logging.info(f"Salesforce: Using MOCKED SOQL query: {soql_query}")
        if "from contact where email" in soql_query.lower():
            # Simulate finding the contact based on email in mock data if needed, or just return the generic one
            # For simplicity, we return the generic mock contact for any email query
            return MOCK_CONTACT_BY_EMAIL
        elif "from case where contactid" in soql_query.lower():
            return MOCK_CASES_BY_CONTACT_ID
        else:
            return MOCK_NO_RECORDS_FOUND

    query_endpoint = f"{_instance_url}/services/data/{SALESFORCE_API_VERSION}/query"
    params = {"q": soql_query}
    headers = {
        "Authorization": f"Bearer {_access_token}",
        "Content-Type": "application/json"
    }

    logging.info(f"Salesforce: Executing SOQL query: {soql_query} at {query_endpoint}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(query_endpoint, params=params, headers=headers) as response:
                response_data = await response.json()
                if response.status == 200:
                    logging.info(f"Salesforce: SOQL query successful. Records returned: {response_data.get('totalSize', 0)}")
                    return response_data
                else:
                    logging.error(f"Salesforce: SOQL query failed. Status: {response.status}, Response: {response_data}")
                    return None # Or response_data to see error details
    except aiohttp.ClientConnectorError as e:
        logging.error(f"Salesforce: Connection error during SOQL query: {e}")
        return None
    except Exception as e:
        logging.error(f"Salesforce: Unexpected error during SOQL query: {e}")
        return None

async def get_contact_by_email(email: str) -> dict | None:
    """
    Retrieves a Salesforce Contact by email address.

    Args:
        email: The email address of the contact to find.

    Returns:
        A dictionary containing contact data if found, otherwise None.
    """
    # Sanitize email for SOQL query to prevent injection (though parameters are usually better)
    # For this context, simple escaping is shown. Use parameterized queries if library supports.
    sanitized_email = email.replace("'", "\\'")
    soql = f"SELECT Id, Name, Email, Phone FROM Contact WHERE Email = '{sanitized_email}' LIMIT 1"

    response = await query_salesforce(soql)

    if response and response.get("totalSize", 0) > 0 and response.get("records"):
        return response["records"][0]
    elif response and response.get("totalSize", 0) == 0:
        logging.info(f"Salesforce: No contact found for email: {email}")
        return None
    else:
        logging.warning(f"Salesforce: Could not retrieve contact for email: {email}. Response: {response}")
        return None

async def get_recent_cases_for_contact(contact_id: str, limit: int = 5) -> list | None:
    """
    Retrieves recent Case objects for a given Contact ID.

    Args:
        contact_id: The Salesforce ID of the Contact.
        limit: The maximum number of cases to retrieve.

    Returns:
        A list of dictionaries, where each dictionary is a Case record, or None if error.
    """
    sanitized_contact_id = contact_id.replace("'", "\\'")
    soql = (
        f"SELECT CaseNumber, Subject, Status, CreatedDate, Description "
        f"FROM Case WHERE ContactId = '{sanitized_contact_id}' "
        f"ORDER BY CreatedDate DESC LIMIT {limit}"
    )
    response = await query_salesforce(soql)

    if response and response.get("records") is not None: # records can be an empty list
        return response["records"]
    else:
        logging.warning(f"Salesforce: Could not retrieve cases for Contact ID: {contact_id}. Response: {response}")
        return None


if __name__ == '__main__':
    # Example usage (for testing this module directly)
    logging.basicConfig(level=logging.INFO)

    async def test_salesforce_client():
        print(f"--- Testing Salesforce Client (Mocked: {config.USE_MOCKED_SALESFORCE}) ---")

        # Test authentication
        auth_success = await authenticate_salesforce()
        print(f"Authentication attempt success: {auth_success}")
        if not auth_success and not config.USE_MOCKED_SALESFORCE:
            print("Cannot proceed with further tests without successful authentication.")
            return

        # Test get_contact_by_email
        test_email = "test@example.com" # This email will be used by the mock if USE_MOCKED_SALESFORCE is True
        if not config.USE_MOCKED_SALESFORCE and config.SALESFORCE_USERNAME != "YOUR_SALESFORCE_USERNAME_PLACEHOLDER":
            # If running live, use the configured username as a test email, assuming it might be a contact
            test_email = config.SALESFORCE_USERNAME
            print(f"Running LIVE test for get_contact_by_email with email: {test_email}")
        else:
            print(f"Running MOCKED test for get_contact_by_email with email: {test_email}")

        contact = await get_contact_by_email(test_email)
        if contact:
            print(f"Contact found: {contact.get('Name')}, ID: {contact.get('Id')}")
            contact_id_for_cases = contact.get("Id")

            if contact_id_for_cases:
                # Test get_recent_cases_for_contact
                print(f"Fetching recent cases for Contact ID: {contact_id_for_cases}...")
                cases = await get_recent_cases_for_contact(contact_id_for_cases)
                if cases is not None: # Empty list is a valid successful response
                    print(f"Found {len(cases)} case(s):")
                    for case in cases:
                        print(f"  - CaseNumber: {case.get('CaseNumber')}, Subject: {case.get('Subject')}, Status: {case.get('Status')}")
                else:
                    print("Failed to retrieve cases or no cases found.")
            else:
                print("Cannot fetch cases as Contact ID was not found.")
        else:
            print(f"No contact found for email: {test_email}")

        # Test a generic query if not mocked
        if not config.USE_MOCKED_SALESFORCE:
            print("Attempting generic SOQL query for Account names (live)...")
            generic_query_result = await query_salesforce("SELECT Id, Name FROM Account LIMIT 3")
            if generic_query_result:
                print(f"Generic query result: {generic_query_result.get('totalSize')} records. First few: {generic_query_result.get('records')}")
            else:
                print("Generic SOQL query failed.")


    asyncio.run(test_salesforce_client())
