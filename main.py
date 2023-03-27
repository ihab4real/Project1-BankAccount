from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import sqlite3
import secrets
import pickle


def generate_account_number():
    """Generate a 16-digit account number."""
    alphabet = "0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(16))


# the purpose of the gui is more user friendly look than the console. it is for the customers yes. the gui firstly
# asks the customer for account number, if the account number is in the system, it opens a new window that displays
# the sentence "Hello Customer!" and below it the account number, and then three buttons for the three main
# operations of the account: deposit, apply interest and withdraw. after them there is a button to show the
# transactions history of the account, once it is clicked, it gives three options: All, In, Out and Failed,
# each one of them is a button that if clicked the transactions of it will be shown with a default of of seven days
# time range that is a dropdown menu that contains: 7 days, 30 days and 90 days to choose from. the default
# transactions type is the "All".
#
# use tkinter.
#
# be creative with the colors!

class TransactionDeclinedError(Exception):
    """
    Exception raised when a transaction is declined by the bank.
    """


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


class ConfirmationNumber:
    def __init__(self, transaction_type, account_number, transaction_time, transaction_id):
        self._transaction_type = transaction_type
        self._account_number = account_number
        self._transaction_time = transaction_time
        self._transaction_id = transaction_id

    @property
    def transaction_id(self):
        return self._transaction_id


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
                # Retrieve the current value of the transaction_id from the database
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'transaction_id'")
                row = cursor.fetchone()
                if row is not None:
                    # Return the retrieved value as an integer
                    return int(row[0])
                else:
                    # if the transaction_id hasn't been saved to the database yet, the value of transaction_id will
                    # start from 0 and increase after each transaction.
                    return 0
            except sqlite3.Error as e:
                raise DataRetrievalError(f"Failed to retrieve data: {e}")

    def save_transaction_id(self, transaction_id):
        with sqlite3.connect(self.db_file) as conn:
            try:
                # Check if a row with key='transaction_id' already exists
                cursor = conn.execute("SELECT value FROM metadata WHERE key = 'transaction_id'")
                row = cursor.fetchone()
                if row is not None:
                    # Update the value of the transaction_id in the database
                    conn.execute("UPDATE metadata SET value = ? WHERE key = 'transaction_id'", (transaction_id,))
                else:
                    # Insert the initial value of the transaction_id into the database
                    conn.execute("INSERT INTO metadata (key, value) VALUES ('transaction_id', ?)", (transaction_id,))
                # Save the changes
                conn.commit()
            except sqlite3.Error as e:
                raise DataInsertionError(f"Failed to insert data: {e}")


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


class Account:
    monthly_interest_rate = Decimal('0.05')
    transaction_id = None

    def __init__(self, account_number, balance, db: DataBase, time_zone):
        self._account_number = account_number
        self._time_zone = time_zone
        self._db = db
        if not self.is_amount_a_number(balance):
            raise ValueError("Invalid balance: balance must be a number or a string representing a number")

        balance = Decimal(balance).quantize(Decimal('.01'))

        if balance < 0:
            raise ValueError("Invalid balance: balance must be a non-negative number")

        self._balance = balance

        self._transactions = []
        self._deposit_type = 'D'
        self._interest_deposit_type = 'I'
        self._withdrawal_type = 'W'
        self._declined_transaction_type = 'X'

    @property
    def account_number(self):
        return self._account_number

    @property
    def balance(self):
        return self._balance

    @property
    def db(self):
        return self._db

    @property
    def time_zone(self):
        return self._time_zone

    def deposit(self, amount):
        confirmation_number = ConfirmationNumber(transaction_type=self._deposit_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        if not self.is_amount_a_number(amount):
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError("Invalid amount: amount must be a number or a string representing a number")

        amount = Decimal(amount).quantize(Decimal('.01'))

        if amount < 0:
            amount = 0

        self._balance += amount
        print(f"Deposited {amount}. New balance is {self._balance}")
        self._transactions.append(confirmation_number)

    def apply_interest(self):
        confirmation_number = ConfirmationNumber(transaction_type=self._interest_deposit_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        interest = self._balance * self.monthly_interest_rate
        self._balance += interest.quantize(Decimal(".01"))
        print(f"Applied {self.monthly_interest_rate * 100}% interest. New balance is {self._balance}")
        self._transactions.append(confirmation_number)

    def withdraw(self, amount):
        confirmation_number = ConfirmationNumber(transaction_type=self._withdrawal_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        if not self.is_amount_a_number(amount):
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError("Invalid amount: amount must be a number or a string representing a number.")

        amount = Decimal(amount).quantize(Decimal('.01'))

        if amount <= 0:
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError('Invalid amount: amount must be a positive number.')

        if amount > self._balance:
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError(
                'Invalid amount: cannot withdraw an amount of money higher than the balance.')

        self._balance -= amount
        print(f"Withdrew {amount}. New balance is {self._balance}")
        self._transactions.append(confirmation_number)

    @staticmethod
    def is_amount_a_number(amount):
        try:
            Decimal(amount).quantize(Decimal('.01'))
            return True
        except InvalidOperation:
            return False

    def _transaction_failure(self, confirmation_number):
        confirmation_number._transaction_type = self._declined_transaction_type
        self._transactions.append(confirmation_number)

    def __repr__(self):
        return f'{type(self).__name__}({self._account_number}, {self.balance}, {self._db}, {self._time_zone})'


class Customer:
    def __init__(self, f_name, l_name, account):
        self.f_name = f_name
        self.l_name = l_name
        self._account = account

    @property
    def fullname(self):
        return f'{self.f_name} {self.l_name}'


if __name__ == '__main__':
    acc = Account(generate_account_number(), 2000, DataBase('mydb.db'), 'MST')
    print(type(acc))
    acc = pickle.dumps(acc)
    print(type(acc))
    acc = pickle.loads(acc)
    print(type(acc))  # pickled Account objects to store them in the accounts table.
