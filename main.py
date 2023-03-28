from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import secrets
import pickle
from database import DataBase


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


class ConfirmationNumber:
    def __init__(self, transaction_type, account_number, transaction_time, transaction_id):
        self._transaction_type = transaction_type
        self._account_number = account_number
        self._transaction_time = transaction_time
        self._transaction_id = transaction_id

    @property
    def transaction_id(self):
        return self._transaction_id

    def __str__(self):
        formatted_time = self._transaction_time.strftime("%Y%m%d%H%M%S")
        transaction_id_plus_one = str(self._transaction_id + 1)
        return f"{self._transaction_type}-{self._account_number}-{formatted_time}-{transaction_id_plus_one}"

    def __repr__(self):
        return f"ConfirmationNumber({self._transaction_type}, {self._account_number}, {self._transaction_time}," \
               f" {self._transaction_id})"


class Account:
    monthly_interest_rate = Decimal('0.05')
    transaction_id = None

    def __init__(self, account_number, balance, db: DataBase, time_zone):
        self._account_number = account_number
        self._time_zone = timezone(timedelta(hours=time_zone))
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
        return confirmation_number

    def apply_interest(self):
        confirmation_number = ConfirmationNumber(transaction_type=self._interest_deposit_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        interest = self._balance * self._db.load_monthly_interest_rate()
        self._balance += interest
        print(f"Applied {self.monthly_interest_rate * 100}% interest. New balance is {self._balance}")
        self._transactions.append(confirmation_number)
        return confirmation_number

    @classmethod
    def update_monthly_interest_rate(cls):
        ...

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
        return confirmation_number

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

    def break_down_confirmation_number(self, confirmation_number):
        transaction_type, account_number, transaction_time, transaction_id = confirmation_number
        local_transaction_time = transaction_time.astimezone(self._time_zone)
        return *confirmation_number, transaction_time.astimezone(self._time_zone)

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
    acc = Account('140568', 100.00, DataBase('mydb.db'), -7)
    cn = acc.deposit(50.00)
    print(acc.balance)
    print(cn)
