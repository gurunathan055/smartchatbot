import logging
import snowflake.connector
from snowflake.connector.errors import ProgrammingError
import config # Import configuration
import os # For private key path expansion

# --- Mocked Snowflake Data ---
MOCK_KB_ANSWER = {
    "answer": "This is a mocked answer from Snowflake for your query about category '{category}' with keywords '{keywords}'. The sky is blue due to Rayleigh scattering."
}
MOCK_NO_KB_ANSWER_FOUND = {"answer": None}
# --- End Mocked Snowflake Data ---

# Store connection object globally or pass around; for simplicity, a global approach for this example
_snowflake_connection = None

def _get_private_key_bytes():
    """Reads private key bytes from the path specified in config, handling passphrase."""
    if not config.SNOWFLAKE_PRIVATE_KEY_PATH:
        return None

    private_key_path = os.path.expanduser(config.SNOWFLAKE_PRIVATE_KEY_PATH)
    if not os.path.exists(private_key_path):
        logging.error(f"Snowflake: Private key file not found at {private_key_path}")
        return None

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        with open(private_key_path, "rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=(
                    config.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode()
                    if config.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
                    else None
                ),
                backend=default_backend(),
            )

        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pkb
    except Exception as e:
        logging.error(f"Snowflake: Failed to read or decrypt private key: {e}")
        return None


def connect_snowflake():
    """
    Establishes a connection to Snowflake using parameters from config.py.
    Prioritizes Key-Pair authentication, then Username/Password.
    Returns a Snowflake connection object or a mock connection object/None.
    """
    global _snowflake_connection
    if _snowflake_connection:
        # Ping the connection to ensure it's still alive before reusing
        try:
            if _snowflake_connection.is_closed():
                logging.info("Snowflake: Connection was closed, attempting to reconnect.")
                _snowflake_connection = None # Force reconnect
            else:
                _snowflake_connection.cursor().execute("SELECT 1")
                logging.info("Snowflake: Reusing existing connection.")
                return _snowflake_connection
        except Exception as e:
            logging.warning(f"Snowflake: Existing connection check failed ({e}), attempting to reconnect.")
            _snowflake_connection = None # Force reconnect


    if config.USE_MOCKED_SNOWFLAKE:
        logging.info("Snowflake: Using MOCKED connection.")
        # Return a mock connection object that minimally supports cursor() -> mock_cursor
        class MockCursor:
            def execute(self, sql, params=None): logging.info(f"MockCursor: Execute SQL: {sql} with params: {params}"); return self
            def fetchall(self): logging.info("MockCursor: Fetchall"); return []
            def fetchone(self): logging.info("MockCursor: Fetchone"); return None
            def close(self): logging.info("MockCursor: Close")
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): self.close()

        class MockConnection:
            def cursor(self, cursor_class=None): return MockCursor()
            def close(self): logging.info("MockConnection: Close")
            def is_closed(self): logging.info("MockConnection: is_closed called"); return False
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): self.close()

        _snowflake_connection = MockConnection()
        return _snowflake_connection

    connection_params = {
        "user": config.SNOWFLAKE_USER,
        "account": config.SNOWFLAKE_ACCOUNT,
        "warehouse": config.SNOWFLAKE_WAREHOUSE,
        "database": config.SNOWFLAKE_DATABASE,
        "schema": config.SNOWFLAKE_SCHEMA,
    }
    if config.SNOWFLAKE_ROLE:
        connection_params["role"] = config.SNOWFLAKE_ROLE

    private_key_bytes = None
    if config.SNOWFLAKE_PRIVATE_KEY_PATH:
        logging.info("Snowflake: Attempting Key-Pair authentication.")
        private_key_bytes = _get_private_key_bytes()
        if private_key_bytes:
            connection_params["private_key"] = private_key_bytes
        else:
            logging.error("Snowflake: Private key path provided, but failed to load key. Cannot use Key-Pair auth.")
            # Fallback to password if available, or fail
            if not config.SNOWFLAKE_PASSWORD:
                 return None

    if not private_key_bytes and config.SNOWFLAKE_PASSWORD: # Fallback or primary if no key path
        logging.info("Snowflake: Attempting Username/Password authentication.")
        connection_params["password"] = config.SNOWFLAKE_PASSWORD
    elif not private_key_bytes and not config.SNOWFLAKE_PASSWORD:
        logging.error("Snowflake: Neither Private Key Path nor Password provided for authentication.")
        return None

    try:
        logging.info(f"Snowflake: Connecting to account '{config.SNOWFLAKE_ACCOUNT}' with user '{config.SNOWFLAKE_USER}'.")
        conn = snowflake.connector.connect(**connection_params)
        _snowflake_connection = conn
        logging.info("Snowflake: Connection successful.")
        return conn
    except ProgrammingError as e:
        logging.error(f"Snowflake: ProgrammingError during connection: {e}")
    except Exception as e:
        logging.error(f"Snowflake: Failed to connect to Snowflake: {e}")
    return None


def query_snowflake_data(sql_query: str, params=None) -> list | None:
    """
    Executes a SQL query against Snowflake and fetches all results.

    Args:
        sql_query: The SQL query string.
        params: Optional parameters for binding to the SQL query.

    Returns:
        A list of dictionaries (if DictCursor is used) representing the rows,
        or None if an error occurs or if mocked and no specific mock matches.
    """
    if config.USE_MOCKED_SNOWFLAKE:
        logging.info(f"Snowflake: Using MOCKED SOQL query: {sql_query} with params: {params}")
        if "from knowledge_base" in sql_query.lower() and params:
            # Simulate keyword matching for the mock
            category_mock = params[0] if isinstance(params, (list, tuple)) and len(params) > 0 else "unknown"
            keywords_mock = params[1] if isinstance(params, (list, tuple)) and len(params) > 1 else "unknown"

            # A very basic mock: if keywords are "sky color", return the specific answer
            if "sky" in keywords_mock.lower() and "color" in keywords_mock.lower():
                 return [{"ANSWER": MOCK_KB_ANSWER["answer"].format(category=category_mock, keywords=keywords_mock)}]
            else: # Generic "not found" for other KB queries in mock mode
                 return [] # Simulate no rows found
        return [] # Default empty list for other mocked queries

    conn = connect_snowflake()
    if not conn:
        return None

    results = None
    try:
        # Using 'with' ensures cursor is closed
        with conn.cursor(snowflake.connector.DictCursor) as cur:
            logging.info(f"Snowflake: Executing query: {sql_query} with params: {params}")
            cur.execute(sql_query, params)
            results = cur.fetchall()
            logging.info(f"Snowflake: Query executed. Fetched {len(results)} rows.")
    except ProgrammingError as e:
        logging.error(f"Snowflake: ProgrammingError during query execution: {e}")
    except Exception as e:
        logging.error(f"Snowflake: An error occurred during query execution: {e}")
    finally:
        # Connection closure can be handled at a higher level or after a period of inactivity
        # For this example, we might close it if it was opened just for this query and is not a persistent one.
        # However, the connect_snowflake function now tries to reuse existing connections.
        # If it created a new one and it's not managed by a 'with' at a higher scope, it should be closed.
        # For simplicity here, we assume connection management is handled by the caller or a higher-level construct.
        # If conn was newly established by connect_snowflake() and not reused, it should be closed.
        # This part needs careful thought in a real application.
        # For now, if it's not the global one that was already there, we close it.
        pass # Let the global connection be managed or closed explicitly elsewhere.

    return results


async def get_knowledge_answer(category: str, keywords_str: str) -> str | None:
    """
    Queries a hypothetical 'knowledge_base' table in Snowflake.

    Args:
        category: The category to search within.
        keywords_str: A string of keywords to search for in the question/content.

    Returns:
        An answer string if found, otherwise None.
    """
    # Example: searching for any keyword using ILIKE.
    # For multiple keywords, one might construct multiple ILIKE clauses or use other text search features.
    # For simplicity, let's assume keywords_str is a single keyword phrase for now.
    # A more robust solution might split keywords_str and build dynamic ILIKE clauses.

    # Simple approach: use the first keyword or the whole string
    # In a real scenario, you'd want better keyword processing.
    search_term = f"%{keywords_str.split()[0]}%" if keywords_str.split() else "%"
    # Or search for the whole phrase: search_term = f"%{keywords_str}%"

    # Using %s for client-side binding (default for snowflake-connector-python if paramstyle not changed)
    sql = "SELECT answer FROM knowledge_base WHERE category = %s AND question ILIKE %s LIMIT 1"
    params = (category, search_term)

    # query_snowflake_data is synchronous, but this function is async to fit into bot's async flow.
    # In a real bot, you might run synchronous DB calls in a thread pool executor.
    # For this example, we'll call it directly, assuming it's okay for the execution model.
    # If snowflake_client itself was made async with aiohttp, this would be await.
    # Since snowflake.connector is blocking, we'd use loop.run_in_executor for true async.
    # For this subtask, we'll keep it simple and call the sync function.
    # This will block the event loop if the DB call is long.

    # Correct way to call blocking IO in an async function:
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, query_snowflake_data, sql, params)

    if data and len(data) > 0:
        return data[0].get("ANSWER") # Assuming DictCursor, so result is dict
    return None

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    logging.basicConfig(level=logging.INFO)

    async def test_snowflake_kb():
        print(f"--- Testing Snowflake Knowledge Base (Mocked: {config.USE_MOCKED_SNOWFLAKE}) ---")

        # Test a known mocked query
        if config.USE_MOCKED_SNOWFLAKE:
            answer = await get_knowledge_answer("general", "sky color")
            print(f"Mocked KB Answer (sky color): {answer}")

            answer_other = await get_knowledge_answer("tech", "python")
            print(f"Mocked KB Answer (python): {answer_other}")


        # Example for a live test (ensure credentials and table exist)
        # This part would only run meaningfully if USE_MOCKED_SNOWFLAKE is False
        # and Snowflake is configured with a 'knowledge_base' table.
        if not config.USE_MOCKED_SNOWFLAKE:
            print("\nAttempting LIVE KB query (ensure 'knowledge_base' table exists with 'category', 'question', 'answer' columns)...")
            # You would need to insert some data into your Snowflake 'knowledge_base' table first
            # For example: INSERT INTO knowledge_base (category, question, answer) VALUES ('greetings', 'What is your name?', 'I am a friendly bot.');
            live_answer = await get_knowledge_answer("greetings", "name")
            if live_answer:
                print(f"Live KB Answer (name): {live_answer}")
            else:
                print("Live KB Answer (name): Not found or query failed.")

            # Test a non-existent entry
            live_answer_fail = await get_knowledge_answer("nonexistent", "blah")
            if live_answer_fail:
                 print(f"Live KB Answer (nonexistent): {live_answer_fail}") # Should not happen
            else:
                print("Live KB Answer (nonexistent): Correctly not found or query failed.")


    asyncio.run(test_snowflake_kb())
