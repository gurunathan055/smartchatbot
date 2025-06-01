# Snowflake Configuration for Azure Bot Integration

For the Azure Bot to connect to and retrieve data from Snowflake using the `snowflake-connector-python` library, the following configuration settings are required. These should be set as environment variables, which will be loaded by `config.py`.

## Required Snowflake Settings:

1.  **`SNOWFLAKE_USER`**:
    *   **Description**: The username for the Snowflake account.
    *   **Source**: Your Snowflake account administrator.
    *   **Example**: `YOUR_SNOWFLAKE_USER_PLACEHOLDER` (replace with actual username)

2.  **`SNOWFLAKE_ACCOUNT`**:
    *   **Description**: Your Snowflake account identifier. This is typically in the format `youraccountid` or `youraccountid.region.cloudprovider` (e.g., `xy12345.us-east-1.aws`). Do **not** include `snowflakecomputing.com`.
    *   **Source**: Provided by Snowflake (visible in your Snowflake URL).
    *   **Example**: `YOUR_SNOWFLAKE_ACCOUNT_PLACEHOLDER` (replace with actual account identifier)

3.  **`SNOWFLAKE_WAREHOUSE`**:
    *   **Description**: The default Snowflake warehouse to use for queries. The specified user must have USAGE permission on this warehouse.
    *   **Source**: Your Snowflake environment.
    *   **Example**: `YOUR_SNOWFLAKE_WAREHOUSE_PLACEHOLDER`

4.  **`SNOWFLAKE_DATABASE`**:
    *   **Description**: The default Snowflake database to use.
    *   **Source**: Your Snowflake environment.
    *   **Example**: `YOUR_SNOWFLAKE_DATABASE_PLACEHOLDER`

5.  **`SNOWFLAKE_SCHEMA`**:
    *   **Description**: The default Snowflake schema within the specified database.
    *   **Source**: Your Snowflake environment.
    *   **Example**: `YOUR_SNOWFLAKE_SCHEMA_PLACEHOLDER`

## Authentication Methods:

You need to configure **one** of the following authentication methods:

**A. Username/Password Authentication:**

*   **`SNOWFLAKE_PASSWORD`**:
    *   **Description**: The password for the `SNOWFLAKE_USER`.
    *   **Source**: Your Snowflake user credentials.
    *   **Example**: (Leave blank if using Key-Pair authentication, otherwise set your password)

**B. Key-Pair Authentication (Recommended for server-to-server):**

*   **`SNOWFLAKE_PRIVATE_KEY_PATH`**:
    *   **Description**: The absolute or relative path to your RSA private key file (PEM format). The public key part must have been assigned to the `SNOWFLAKE_USER` in Snowflake.
    *   **Source**: You generate an RSA key pair. The public key is added to the Snowflake user profile.
    *   **Example**: `~/.ssh/snowflake_rsa_key.p8` or `/path/to/your/private_key.pem` (Leave blank if using Username/Password).
*   **`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`**:
    *   **Description**: The passphrase used to encrypt your private key file, if it is encrypted.
    *   **Source**: Defined when you created your encrypted private key.
    *   **Example**: (Leave blank if your private key is not encrypted).

## Optional Settings:

*   **`SNOWFLAKE_ROLE`**:
    *   **Description**: The default Snowflake role to use for the session after connecting. If not specified, the user's default role will be used.
    *   **Source**: Your Snowflake role configuration.
    *   **Example**: `SYSADMIN` or `CUSTOM_BOT_ROLE` (Leave blank to use default role)

## Running the Bot with Live Snowflake Data:

To run the bot with live Snowflake data:
1.  Ensure the environment variables listed above are set with your actual Snowflake user, account, warehouse, database, schema, and authentication details.
2.  If using Key-Pair authentication, make sure the `SNOWFLAKE_PRIVATE_KEY_PATH` is correctly pointing to your private key file and `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` is set if your key is encrypted. The public key must be assigned to the Snowflake user.
3.  If using Username/Password, ensure `SNOWFLAKE_PASSWORD` is set and `SNOWFLAKE_PRIVATE_KEY_PATH` is empty or not set.
4.  The `USE_MOCKED_SNOWFLAKE` flag in `config.py` should then evaluate to `False`.

If essential configurations like `SNOWFLAKE_USER`, `SNOWFLAKE_ACCOUNT`, or valid authentication details (either password or private key path) are missing or are placeholders, `USE_MOCKED_SNOWFLAKE` will be `True`, and the Snowflake client functions will return mocked data.

**Example: Setting Environment Variables (Linux/macOS for Key-Pair Auth)**
```bash
export SNOWFLAKE_USER="your_user"
export SNOWFLAKE_ACCOUNT="your_account_identifier"
export SNOWFLAKE_WAREHOUSE="your_warehouse"
export SNOWFLAKE_DATABASE="your_database"
export SNOWFLAKE_SCHEMA="your_schema"
export SNOWFLAKE_PRIVATE_KEY_PATH="~/.ssh/your_snowflake_key.p8"
# export SNOWFLAKE_PRIVATE_KEY_PASSPHRASE="your_key_passphrase" # If key is encrypted
# export SNOWFLAKE_ROLE="your_role" # Optional
```

**Example: Setting Environment Variables (Linux/macOS for Username/Password Auth)**
```bash
export SNOWFLAKE_USER="your_user"
export SNOWFLAKE_PASSWORD="your_password"
export SNOWFLAKE_ACCOUNT="your_account_identifier"
export SNOWFLAKE_WAREHOUSE="your_warehouse"
export SNOWFLAKE_DATABASE="your_database"
export SNOWFLAKE_SCHEMA="your_schema"
# export SNOWFLAKE_ROLE="your_role" # Optional
```
Adjust for your operating system's method of setting environment variables.
