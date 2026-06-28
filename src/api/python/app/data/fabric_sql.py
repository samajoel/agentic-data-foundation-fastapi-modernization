import logging
import os
import struct
from datetime import datetime, date
from typing import Tuple, Any
from decimal import Decimal

import pyodbc
from azure.identity.aio import AzureCliCredential
from pydantic import BaseModel, ConfigDict

from app.core.auth.azure_credential_utils import get_azure_credential_async


async def get_azure_sql_connection():
    """
    Get a connection to Azure SQL Server using DefaultAzureCredential.

    Returns:
        Connection: Database connection object for Azure SQL.
    """
    sql_server = os.getenv("AZURE_SQLDB_SERVER") or os.getenv("SQLDB_SERVER")
    sql_database = os.getenv("AZURE_SQLDB_DATABASE") or os.getenv("SQLDB_DATABASE")
    driver18 = "ODBC Driver 18 for SQL Server"
    driver17 = "ODBC Driver 17 for SQL Server"
    api_uid = os.getenv("API_UID", "")

    credential = await get_azure_credential_async(client_id=api_uid)
    token = await credential.get_token("https://database.windows.net/.default")
    await credential.close()

    token_bytes = token.token.encode("utf-16-LE")
    token_struct = struct.pack(
        f"<I{len(token_bytes)}s",
        len(token_bytes),
        token_bytes
    )
    SQL_COPT_SS_ACCESS_TOKEN = 1256

    try:
        connection_string = f"DRIVER={{{driver18}}};SERVER={sql_server};DATABASE={sql_database};"
        conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        return conn
    except Exception:
        try:
            connection_string = f"DRIVER={{{driver17}}};SERVER={sql_server};DATABASE={sql_database};"
            conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
            return conn
        except Exception as e:
            logging.info("AZURE-SQL: Failed to connect to Azure SQL Database: %s", e)
            return None


async def get_fabric_db_connection():
    """
    Get a connection to the Fabric SQL database.

    Returns:
        Connection: Database connection object, or None if connection fails.
    """
    app_env = os.getenv("APP_ENV", "prod").lower()
    database = os.getenv("FABRIC_SQL_DATABASE")
    server = os.getenv("FABRIC_SQL_SERVER")
    driver17 = "ODBC Driver 17 for SQL Server"
    driver18 = "ODBC Driver 18 for SQL Server"
    api_uid = os.getenv("API_UID", "")
    fabric_sql_connection_string18 = os.getenv("FABRIC_SQL_CONNECTION_STRING", "")
    fabric_sql_connection_string17 = (
        f"DRIVER={driver17};SERVER={server};DATABASE={database};"
        f"UID={api_uid};Authentication=ActiveDirectoryMSI"
    )

    try:
        conn = None
        try:
            if app_env == 'dev':
                credential = AzureCliCredential()
                try:
                    token = await credential.get_token("https://database.windows.net/.default")
                    token_bytes = token.token.encode("utf-16-LE")
                    token_struct = struct.pack(
                        f"<I{len(token_bytes)}s",
                        len(token_bytes),
                        token_bytes
                    )
                    SQL_COPT_SS_ACCESS_TOKEN = 1256
                    connection_string = f"DRIVER={driver18};SERVER={server};DATABASE={database};"
                    conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
                finally:
                    await credential.close()
            else:
                conn = pyodbc.connect(fabric_sql_connection_string18)
        except Exception:
            if app_env == 'dev':
                credential = AzureCliCredential()
                try:
                    token = await credential.get_token("https://database.windows.net/.default")
                    token_bytes = token.token.encode("utf-16-LE")
                    token_struct = struct.pack(
                        f"<I{len(token_bytes)}s",
                        len(token_bytes),
                        token_bytes
                    )
                    SQL_COPT_SS_ACCESS_TOKEN = 1256
                    connection_string = f"DRIVER={driver17};SERVER={server};DATABASE={database};"
                    conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
                finally:
                    await credential.close()
            else:
                conn = pyodbc.connect(fabric_sql_connection_string17)

        return conn
    except pyodbc.Error as e:
        logging.info("FABRIC-SQL:Failed to connect Fabric SQL Database: %s", e)
        return None


async def get_db_connection():
    """
    Get a database connection based on deployment mode.

    When IS_WORKSHOP is true, uses Azure SQL Server.
    When IS_WORKSHOP is false or not set, uses Fabric SQL.

    Returns:
        Connection: Database connection object, or None if connection fails.
    """
    is_workshop = os.getenv("IS_WORKSHOP", "false").lower() == "true"
    is_azure_only = os.getenv("AZURE_ENV_ONLY", "true").lower() == "true"

    if is_workshop and is_azure_only:
        logging.info("Workshop deployment mode: Using Azure SQL Server")
        return await get_azure_sql_connection()
    else:
        logging.info("Standard deployment mode: Using Fabric SQL")
        return await get_fabric_db_connection()


async def run_nonquery_params(sql_query, params: Tuple[Any, ...] = ()):
    """
    Execute a SQL non-query operation like DELETE, INSERT, or UPDATE.

    Args:
        sql_query (str): The SQL query to execute with parameter placeholders.
        params (Tuple[Any, ...]): Parameters to bind to the query.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    conn = await get_db_connection()
    if conn is None:
        logging.error("Failed to establish database connection")
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, params)
        conn.commit()
        return True
    except Exception as e:
        logging.error("Error executing SQL query: %s", e)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def run_query_params(sql_query, params: Tuple[Any, ...] = ()):
    """
    Execute parameterized SQL query and return results as list of dictionaries.

    Args:
        sql_query (str): The SQL query to execute with parameter placeholders.
        params (Tuple[Any, ...]): Parameters to bind to the query.

    Returns:
        list: List of dictionaries containing query results, or None if an error occurs.
    """
    conn = await get_db_connection()
    if conn is None:
        logging.error("Failed to establish database connection")
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, params)
        columns = [desc[0] for desc in cursor.description]
        result = []
        for row in cursor.fetchall():
            row_dict = {}
            for col_name, value in zip(columns, row):
                if isinstance(value, (datetime, date)):
                    row_dict[col_name] = value.isoformat()
                elif isinstance(value, Decimal):
                    row_dict[col_name] = float(value)
                else:
                    row_dict[col_name] = value
            result.append(row_dict)

        return result
    except Exception as e:
        logging.error("Error executing SQL query: %s", e)
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


class SqlQueryTool(BaseModel):
    """SQL query tool for executing database queries using Agent Framework."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pyodbc_conn: pyodbc.Connection

    async def run_sql_query(self, sql_query):
        """Execute parameterized SQL query and return results as list of dictionaries."""
        logger = logging.getLogger(__name__)
        try:
            cursor = self.pyodbc_conn.cursor()
            cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            result = []
            for row in cursor.fetchall():
                row_dict = {}
                for col_name, value in zip(columns, row):
                    if isinstance(value, (datetime, date)):
                        row_dict[col_name] = value.isoformat()
                    elif isinstance(value, Decimal):
                        row_dict[col_name] = float(value)
                    else:
                        row_dict[col_name] = value
                result.append(row_dict)
            logger.info("Chat Agent - Result of SQL query: %s", result)
            return result
        except Exception as e:
            logging.error("Error executing SQL query: %s", e)
            return None
        finally:
            if cursor:
                cursor.close()

    async def execute_sql(self, sql_query):
        """Alias for run_sql_query. Execute SQL query and return results as list of dictionaries."""
        return await self.run_sql_query(sql_query)
