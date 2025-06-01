# Salesforce Configuration for Azure Bot Integration

For the Azure Bot to connect to and retrieve data from Salesforce, the following configuration settings are required. These should be set as environment variables, which will be loaded by `config.py`.

## Required Salesforce Settings:

1.  **`SALESFORCE_CLIENT_ID`**:
    *   **Description**: The Consumer Key of your Salesforce Connected App.
    *   **Source**: Obtained from the Salesforce Connected App definition (Setup -> App Manager -> View your Connected App).
    *   **Example**: `YOUR_SALESFORCE_CLIENT_ID_PLACEHOLDER` (replace with actual value)

2.  **`SALESFORCE_CLIENT_SECRET`**:
    *   **Description**: The Consumer Secret of your Salesforce Connected App.
    *   **Source**: Obtained from the Salesforce Connected App definition.
    *   **Example**: `YOUR_SALESFORCE_CLIENT_SECRET_PLACEHOLDER` (replace with actual value)

3.  **`SALESFORCE_USERNAME`**:
    *   **Description**: The username of the Salesforce user account the bot will use to authenticate. This user must have appropriate permissions to access the required data (Contacts, Cases).
    *   **Source**: A dedicated Salesforce user account for this integration is recommended.
    *   **Example**: `your_bot_user@example.com`

4.  **`SALESFORCE_PASSWORD`**:
    *   **Description**: The password for the Salesforce user specified in `SALESFORCE_USERNAME`. **Important:** This often needs to be the user's password concatenated with their Salesforce security token (e.g., `mypasswordMYSECURITYTOKEN`). The security token is required if the bot is accessing Salesforce from an IP address not whitelisted in Salesforce's Network Access settings.
    *   **Source**: Password for the Salesforce user. The security token can be reset/found in the user's personal settings in Salesforce.
    *   **Example**: `YOUR_SALESFORCE_PASSWORD_TOKEN_PLACEHOLDER` (replace with actual password + security token)

5.  **`SALESFORCE_LOGIN_URL`**:
    *   **Description**: The Salesforce login URL. For production environments, this is typically `https://login.salesforce.com`. For sandboxes, it's `https://test.salesforce.com`.
    *   **Source**: Depends on whether you are using a production or sandbox Salesforce org.
    *   **Default in `config.py`**: `https://login.salesforce.com` (can be overridden by environment variable).

## Setting up a Salesforce Connected App:

To obtain the `SALESFORCE_CLIENT_ID` and `SALESFORCE_CLIENT_SECRET`, you need to create and configure a "Connected App" in your Salesforce organization:

1.  **Navigate to Setup:** In Salesforce, go to Setup.
2.  **App Manager:** Search for "App Manager" and open it.
3.  **New Connected App:** Click "New Connected App".
4.  **Basic Information:**
    *   **Connected App Name:** (e.g., `AzureBotIntegration`)
    *   **API Name:** (e.g., `Azure_Bot_Integration`)
    *   **Contact Email:** Your email address.
5.  **API (Enable OAuth Settings):**
    *   Check **Enable OAuth Settings**.
    *   **Callback URL:** For the Username-Password flow, this is often not strictly used for redirection but needs to be a valid HTTPS URL. You can use a placeholder like `https://localhost/oauth/callback` or your bot's URL if applicable for other flows in the future.
    *   **Selected OAuth Scopes:** Add necessary scopes. For data access, common scopes include:
        *   `Access and manage your data (api)`
        *   `Perform requests on your behalf at any time (refresh_token, offline_access)` (if you plan to use refresh tokens, though the current Username-Password flow example doesn't explicitly implement refresh token logic).
6.  **Save** the Connected App. It might take a few minutes for the changes to propagate.
7.  **Consumer Key and Consumer Secret:** After saving, you will find the "Consumer Key" (this is your `SALESFORCE_CLIENT_ID`) and you can click to reveal the "Consumer Secret" (this is your `SALESFORCE_CLIENT_SECRET`). Securely store these.

## Security Token:

*   If you are accessing Salesforce from an IP address that is not whitelisted under Setup -> Security -> Network Access, you will need to append the user's security token to their password.
*   Each user can find/reset their security token from their personal settings in Salesforce (My Personal Information -> Reset My Security Token).

## Running the Bot with Live Salesforce Data:

To run the bot with live Salesforce data, ensure the environment variables listed above are set with your actual Connected App and user credentials. Then, in `config.py`, the `USE_MOCKED_SALESFORCE` flag should evaluate to `False`.

If these environment variables are not set, or if placeholders are detected, `USE_MOCKED_SALESFORCE` will be `True`, and the Salesforce client functions will return mocked data.
