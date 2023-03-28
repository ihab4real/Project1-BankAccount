from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3
import pickle


class TableCreationError(Exception):
    """
    Exception raised when there is an error creating a table in the database.
    """


class DataInsertionError(Exception):
    """
    Exception raised when there is an error inserting data into the database.
    """


class DataRetrievalError(Exception):
    """
    Raised when there is an error retrieving data from a database or other data source.
    """


class DataBase:
    def __init__(self, db_file):
        self.db_file = db_file

    def create_customers_table(self):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the customers table already exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
                if cursor.fetchone() is not None:
                    # The customers table already exists, so return without re-creating it
                    return

                # Create the customers table
                conn.execute('''CREATE TABLE customers
                                 (id INTEGER PRIMARY KEY AUTO_INCREMENT,
                                  f_name TEXT,
                                  l_name TEXT,
                                  age INTEGER,
                                  gender TEXT,
                                  mobile_number TEXT,
                                  address TEXT,
                                  account_number TEXT NOT NULL)''')
                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise TableCreationError(f"Failed to create table: {e}")

    def add_customer(self, f_name, l_name, age, gender, mobile_number, address, account_number):
        # Insert a new customer into the customers table
        with sqlite3.connect(self.db_file) as conn:
            try:
                conn.execute(
                    "INSERT INTO customers (f_name, l_name, age, gender, mobile_number, address, account_number) "
                    "VALUES (:fn, :ln, :age, :gn, :mb, :addr, an)",
                    {'fn': f_name,
                     'ln': l_name,
                     'age': age,
                     'gn': gender,
                     'mb': mobile_number,
                     'addr': address,
                     'an': account_number})

                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")

    def create_accounts_table(self):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the accounts table already exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
                if cursor.fetchone() is not None:
                    # The accounts table already exists, so return without creating it
                    return

                # Create the accounts table
                conn.execute('''CREATE TABLE accounts
                                 (id INTEGER PRIMARY KEY,
                                  account_object BLOB,
                                  customer_id INTEGER NOT NULL,
                                  FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE)''')
                # Save the changes
                conn.commit()
            except sqlite3.Error as e:
                raise TableCreationError(f"Failed to create table: {e}")

    def add_account(self, account, customer_id):
        # Insert a new account into the accounts table
        with sqlite3.connect(self.db_file) as conn:
            try:
                conn.execute(
                    "INSERT INTO accounts (id, account_object, customer_id) VALUES (?, ?, ?)",
                    (account.account_number, pickle.dumps(account), customer_id))
                # Save the changes
                conn.commit()
            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")

    def create_transactions_table(self):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the transactions table already exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
                if cursor.fetchone() is not None:
                    # The transactions table already exists, so return without creating it
                    return

                # Create the transactions table
                conn.execute('''CREATE TABLE transactions
                                 (id INTEGER PRIMARY KEY,
                                  account_number TEXT NOT NULL,
                                  type TEXT,
                                  created_at TIMESTAMP,
                                  FOREIGN KEY (account_number) REFERENCES accounts (id) ON DELETE SET NULL)''')
                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise TableCreationError(f"Failed to create table: {e}")

    def add_transaction(self, confirmation_number):
        # Insert a new transaction into the transactions table
        with sqlite3.connect(self.db_file) as conn:
            try:
                conn.execute(
                    "INSERT INTO transactions (id, account_number, type, created_at) VALUES (:id, "
                    ":an, :type, :time)",
                    {'id': confirmation_number.transaction_id,
                     'an': str(confirmation_number.account_number),
                     'type': confirmation_number.transaction_type,
                     'time': confirmation_number.transaction_time})
                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")

    @staticmethod
    def get_confirmation_number_from_row(row):
        from main import ConfirmationNumber

        if row is None:
            return None

        # Otherwise, reconstruct the ConfirmationNumber object and return it
        transaction_id, account_number, transaction_type, transaction_time = row
        confirmation_number = ConfirmationNumber(transaction_type, account_number, transaction_time, transaction_id)
        return confirmation_number

    def get_transactions_by_type(self, account_number, transaction_type, time_range=7):
        with sqlite3.connect(self.db_file) as conn:
            # Check the time range argument
            if time_range == 7:
                days = 7
            elif time_range == 30:
                days = 30
            elif time_range == 90:
                days = 90
            else:
                raise ValueError('Invalid time range')

            # Calculate the time window
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Build the SQL query based on the transaction_type parameter
            if transaction_type == "In":
                query = "SELECT * FROM transactions WHERE account_number = ? AND type IN ('D', 'I')"
            elif transaction_type == "Out":
                query = "SELECT * FROM transactions WHERE account_number = ? AND type = 'W'"
            elif transaction_type == "Failed":
                query = "SELECT * FROM transactions WHERE account_number = ? AND type = 'X'"
            elif transaction_type == "All":
                query = "SELECT * FROM transactions WHERE account_number = ?"
            else:
                raise ValueError("Invalid transaction_type")

            # Add a WHERE clause to the query to filter transactions within the date range
            query += " AND created_at BETWEEN ? AND ?"

            # Add an ORDER BY clause to the query to sort transactions by date in descending order
            query += " ORDER BY created_at DESC"

            try:
                # Execute the SQL query
                cursor = conn.execute(query, (account_number, start_date, end_date))
            except sqlite3.Error as e:
                raise DataRetrievalError(f"Failed to retrieve data: {e}")

            # Yield ConfirmationNumber objects from the query results
            for row in cursor.fetchall():
                yield self.get_confirmation_number_from_row(row)

    def load_transaction_id(self):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the metadata table exists, and create it if not.
                self.__class__.metadata_table_check(conn)

                # Retrieve the current value of the transaction_id from the database
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'transaction_id'")
                row = cursor.fetchone()
                if row is not None:
                    # Return the retrieved value as an integer
                    return int(row[0])
                else:
                    # if the transaction_id hasn't been saved to the database yet, the value of transaction_id will
                    # start from 0 and increase after each transaction.
                    self.save_transaction_id(1)
                    return 0

            except sqlite3.Error as e:
                raise DataRetrievalError(f"Failed to retrieve data: {e}")

    def save_transaction_id(self, transaction_id):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the metadata table exists, and create it if not.
                self.__class__.metadata_table_check(conn)

                # Check if a row with key='transaction_id' already exists
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'transaction_id'")
                row = cursor.fetchone()
                if row is not None:
                    # Update the value of the transaction_id in the database
                    conn.execute("UPDATE metadata SET value = ? WHERE key = 'transaction_id'", (str(transaction_id),))
                else:
                    # Insert the initial value of the transaction_id into the database
                    conn.execute("INSERT INTO metadata (key, value) VALUES ('transaction_id', ?)", (str(transaction_id),))
                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")

    def load_monthly_interest_rate(self):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the metadata table exists, and create it if not.
                self.__class__.metadata_table_check(conn)

                # Retrieve the current value of the monthly_interest_rate from the database
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'monthly_interest_rate'")
                row = cursor.fetchone()
                if row is not None:
                    # Return the retrieved value as a Decimal
                    return Decimal(row[0])
                else:
                    # if the monthly_interest_rate hasn't been saved to the database yet, set it to a default value
                    # of 0.05
                    self.save_monthly_interest_rate('0.05')
                    return Decimal('0.05')

            except sqlite3.Error as e:
                raise DataRetrievalError(f"Failed to retrieve data: {e}")

    def save_monthly_interest_rate(self, monthly_interest_rate):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if the metadata table exists, and create it if not.
                self.__class__.metadata_table_check(conn)

                # Check if a row with key='monthly_interest_rate' already exists
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'monthly_interest_rate'")
                row = cursor.fetchone()
                if row is not None:
                    # Update the value of the monthly_interest_rate in the database
                    conn.execute("UPDATE metadata SET value = ? WHERE key = 'monthly_interest_rate'",
                                 (str(monthly_interest_rate),))
                else:
                    # Insert the initial value of the monthly_interest_rate into the database
                    conn.execute("INSERT INTO metadata (key, value) VALUES ('monthly_interest_rate', ?)",
                                 (str(monthly_interest_rate),))
                # Save the changes
                conn.commit()

            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")

    @staticmethod
    def metadata_table_check(conn):
        # Check if the metadata table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
        table_exists = cursor.fetchone() is not None
        if not table_exists:
            # Create the metadata table if it doesn't exist
            conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
            # Save the changes
            conn.commit()


class DataBaseContextManager:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.conn = sqlite3.connect(self.db.db_file)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val or exc_tb:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
