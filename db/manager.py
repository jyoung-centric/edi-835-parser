"""Database manager for EDI 835 testing and operations."""

import os
import uuid
import json
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json, RealDictCursor
from psycopg2.extensions import register_adapter, AsIs
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()


class DatabaseManager:
    """Manages database connections and operations for EDI 835 testing"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5433,
        database: str = "bot_automation",
        user: str = "bot",
        password: str = "bot_test_password",
        schema: str = "bot"
    ):
        """Initialize database manager with connection parameters"""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.connection = None
        self.cursor = None

    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            # Set search path to bot schema
            self.cursor.execute(f"SET search_path TO {self.schema}, public;")
            self.connection.commit()

            print(f"✅ Connected to PostgreSQL database: {self.database}")
            return True

        except psycopg2.Error as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")

    def test_connection(self) -> bool:
        """Test database connection and schema"""
        try:
            self.cursor.execute("SELECT current_database(), current_schema();")
            result = self.cursor.fetchone()
            print(f"📊 Database: {result['current_database']}, Schema: {result['current_schema']}")

            # Check if payments_835 table exists
            self.cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = 'payments_835';
            """, (self.schema,))

            if self.cursor.fetchone():
                print("✅ Table 'payments_835' exists")
                return True
            else:
                print("❌ Table 'payments_835' not found")
                return False

        except psycopg2.Error as e:
            print(f"❌ Connection test failed: {e}")
            return False

    def clear_all_data(self):
        """Clear all data from test database (for cleanup between test runs)"""
        try:
            # Delete in reverse dependency order
            tables = [
                'cas_adjustments',
                'nm1_entities',
                'plb_adjustments',
                'service_lines',
                'claims',
                'payees',
                'payers',
                'edi_transactions',
                'raw_835_files',
                'payments_835'
            ]

            for table in tables:
                self.cursor.execute(f"DELETE FROM {self.schema}.{table};")

            self.connection.commit()
            print("🧹 All test data cleared from database")

        except psycopg2.Error as e:
            self.connection.rollback()
            print(f"❌ Failed to clear data: {e}")

    def insert_payment_835(
        self,
        file_name: str,
        json_data: Dict[str, Any],
        raw_edi: str
    ) -> Optional[uuid.UUID]:
        """
        Insert parsed EDI 835 data into payments_835 table
        Creates ONE record per transaction (multiple transactions = multiple records)

        Args:
            file_name: Name of the EDI file
            json_data: Parsed JSON data from parse_to_json()
            raw_edi: Raw EDI file content

        Returns:
            UUID of the FIRST inserted record, or None if failed
        """
        try:
            # Generate base file_id for first transaction
            base_file_id = uuid.uuid4()

            # Extract summary fields from JSON
            transactions = json_data.get("interchange", {}).get("transactions", [])

            if not transactions:
                print(f"⚠️  No transactions found in {file_name}")
                return None

            print(f"  📊 Processing {len(transactions)} transaction(s) from {file_name}")

            # Insert ONE payments_835 record per transaction
            first_record_id = None
            for txn_index, transaction in enumerate(transactions):
                # Generate unique file_id per transaction (for idempotency)
                # First transaction uses base UUID, subsequent use uuid5
                if txn_index == 0:
                    file_id = base_file_id
                else:
                    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
                    file_id = uuid.uuid5(namespace, f"{file_name}::txn_{txn_index}")

                bpr = transaction.get("BPR", {})
                trn = transaction.get("TRN", {})

                # Extract payer from N1_loop
                payer_id = None
                n1_loops = transaction.get("N1_loop", [])
                for n1_loop in n1_loops:
                    n1 = n1_loop.get("N1", {})
                    if n1.get("entity_identifier_code") == "PR":  # PR = Payer
                        payer_id = n1.get("identification_code")
                        break

                # Prepare data for insert
                check_number = trn.get("reference_identification")
                payment_date = bpr.get("check_issue_or_eft_effective_date")
                payment_amount = bpr.get("monetary_amount")
                payee_id = trn.get("originating_company_identifier")

                # Insert into payments_835
                # Insert into payments_835 (processed summary)
                insert_query = """
                    INSERT INTO payments_835
                    (file_id, file_name, receive_date_time, check_number, payment_date,
                     payment_amount, payer_id, payee_id, json_transaction)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """

                # Create transaction-specific JSON (single transaction)
                single_transaction_json = {
                    "interchange": {
                        "ISA": json_data.get("interchange", {}).get("ISA"),
                        "GS": json_data.get("interchange", {}).get("GS"),
                        "transactions": [transaction],  # Only this transaction
                        "GE": json_data.get("interchange", {}).get("GE"),
                        "IEA": json_data.get("interchange", {}).get("IEA")
                    }
                }

                self.cursor.execute(insert_query, (
                    file_id,
                    file_name,
                    datetime.now(),
                    check_number,
                    payment_date,
                    payment_amount,
                    payer_id,
                    payee_id,
                    Json(single_transaction_json),
                ))

                result = self.cursor.fetchone()

                # Insert into raw_835_files (raw data)
                raw_insert_query = """
                    INSERT INTO raw_835_files
                    (file_id, receive_date_time, raw_json_transaction, raw_edi)
                    VALUES (%s, %s, %s, %s);
                """
                self.cursor.execute(raw_insert_query, (
                    file_id,
                    datetime.now(),
                    Json(json_data),
                    raw_edi,
                ))

                # Save first record ID to return
                if txn_index == 0:
                    first_record_id = result['id']

                print(f"  💾 Transaction {txn_index + 1}/{len(transactions)}: ID={result['id']}, Check={check_number}, Amount=${payment_amount}")

            self.connection.commit()
            print(f"  ✅ Successfully inserted {len(transactions)} payment record(s)")

            return base_file_id

        except psycopg2.Error as e:
            self.connection.rollback()
            print(f"  ❌ Database insert failed: {e}")
            return None

    def get_payment_count(self) -> int:
        """Get total number of payments in database"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM payments_835;")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except psycopg2.Error as e:
            print(f"❌ Query failed: {e}")
            return 0

    def get_payments_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all payments"""
        try:
            self.cursor.execute("""
                SELECT
                    id,
                    file_name,
                    check_number,
                    payment_date,
                    payment_amount,
                    payer_id,
                    created_date_time,
                    jsonb_array_length(json_transaction->'interchange'->'transactions') as transaction_count
                FROM payments_835
                ORDER BY created_date_time DESC;
            """)

            return self.cursor.fetchall()

        except psycopg2.Error as e:
            print(f"❌ Query failed: {e}")
            return []

    def verify_json_structure(self, file_id: uuid.UUID) -> bool:
        """Verify JSON data structure in database"""
        try:
            self.cursor.execute("""
                SELECT
                    file_name,
                    json_transaction->'interchange'->'transactions' as transactions
                FROM payments_835
                WHERE file_id = %s;
            """, (file_id,))

            result = self.cursor.fetchone()

            if result and result['transactions']:
                print(f"  ✅ JSON structure verified for {result['file_name']}")
                print(f"     Transactions in JSON: {len(result['transactions'])}")
                return True
            else:
                print(f"  ❌ Invalid JSON structure")
                return False

        except psycopg2.Error as e:
            print(f"  ❌ Verification failed: {e}")
            return False


def get_database_manager() -> DatabaseManager:
    """
    Factory function to create DatabaseManager with environment variable support

    Environment variables:
    - DB_HOST (default: localhost)
    - DB_PORT (default: 5433)
    - DB_NAME (default: bot_automation)
    - DB_USER (default: bot)
    - DB_PASSWORD (default: bot_test_password)
    - DB_SCHEMA (default: bot)
    """
    return DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        database=os.getenv("DB_NAME", "bot_automation"),
        user=os.getenv("DB_USER", "bot"),
        password=os.getenv("DB_PASSWORD", "bot_test_password"),
        schema=os.getenv("DB_SCHEMA", "bot")
    )
