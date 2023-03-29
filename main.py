from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, getcontext
import secrets
import pickle
import pytz
from database import DataBase

# getcontext().prec = 2


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


class AccountLimitExceededError(Exception):
    """
    Raised when a customer tries to open more accounts than the allowed limit, which is 3.
    """


class ConfirmationNumber:
    def __init__(self, transaction_type, account_number, transaction_time, transaction_id, amount='0.00'):
        self._transaction_type = transaction_type
        self._account_number = account_number
        self._transaction_time = transaction_time
        self._transaction_id = transaction_id
        self._amount = amount
        self._time_zone = None

    @property
    def account_number(self):
        return self._account_number

    @property
    def transaction_type(self):
        return self._transaction_type

    @property
    def transaction_id(self):
        return self._transaction_id

    @property
    def transaction_time_utc(self):
        return self._transaction_time.isoformat()

    @property
    def transaction_time(self):
        return self._transaction_time

    @property
    def transaction_time_local(self):
        if self._time_zone is None:
            raise AttributeError('This method exists to help other methods in other classes, can not work on its own')
        return self._transaction_time.astimezone(self._time_zone).strftime('%Y-%m-%d %H:%M:%S (%Z%z)')

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, value):
        self._amount = str(value)

    def __str__(self):
        formatted_time = self._transaction_time.strftime("%Y%m%d%H%M%S")
        return f"{self._transaction_type}-{self._account_number}-{formatted_time}-" \
               f"{str(self._transaction_id)}-({self.amount})"

    def __repr__(self):
        return f"ConfirmationNumber({self._transaction_type}, {self._account_number}, {self._transaction_time}," \
               f" {self._transaction_id}, {self.amount})"


class Account:
    monthly_interest_rate = Decimal('0.05')
    transaction_id = None

    def __init__(self, account_number, balance, db: DataBase, time_zone):
        self._account_number = account_number
        self._time_zone = pytz.timezone(time_zone)
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
                                                 transaction_time=datetime.now(tz=pytz.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        if not self.is_amount_a_number(amount):
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError("Invalid amount: amount must be a number or a string representing a number")

        amount = Decimal(amount).quantize(Decimal('.01'))

        if amount < 0:
            amount = Decimal('0.00')

        confirmation_number.amount = amount

        self._balance += amount
        print(f"Deposited {amount}. New balance is {self._balance}")
        self._transactions.append(confirmation_number)
        self._db.add_transaction(confirmation_number)
        return confirmation_number

    def apply_interest(self):
        confirmation_number = ConfirmationNumber(transaction_type=self._interest_deposit_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(tz=pytz.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        interest = (self._balance * self._db.load_monthly_interest_rate()).quantize(Decimal('.01'))
        self._balance += interest

        confirmation_number.amount = interest
        print(f"Applied {self.monthly_interest_rate * 100}% interest. New balance is {self._balance}")
        self._transactions.append(confirmation_number)
        self._db.add_transaction(confirmation_number)
        return confirmation_number

    @classmethod
    def update_monthly_interest_rate(cls):
        ...

    def withdraw(self, amount):
        confirmation_number = ConfirmationNumber(transaction_type=self._withdrawal_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(tz=pytz.utc),
                                                 transaction_id=self._db.load_transaction_id())
        self._db.save_transaction_id(confirmation_number.transaction_id + 1)

        if not self.is_amount_a_number(amount):
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError("Invalid amount: amount must be a number or a string representing a number.")

        amount = Decimal(amount).quantize(Decimal('.01'))

        confirmation_number.amount = amount

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
        self._db.add_transaction(confirmation_number)
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
        self._db.add_transaction(confirmation_number)

    def localize_confirmation_number(self, confirmation_number):
        confirmation_number._time_zone = self.time_zone
        return confirmation_number

    def __repr__(self):
        return f'{type(self).__name__}({self._account_number}, {self.balance}, {self._db}, {self._time_zone})'


class Customer:
    def __init__(self, f_name, l_name, age, gender, mobile_number, address):
        self._f_name = f_name
        self._l_name = l_name
        self._age = age
        self._gender = gender
        self._mobile_number = mobile_number
        self._address = address

    @property
    def fullname(self):
        return f'{self._f_name} {self._l_name}'


class BankEmployee:
    def __init__(self, db):
        self._db = db

    def register_customer(self, f_name, l_name, age, gender, mobile_number, address, email, national_number):
        # check if customer has already reached the accounts limit they can have (3 accounts per user)
        if not self._db.can_customer_have_another_account():
            raise AccountLimitExceededError(f"Customer with national number {national_number} has exceeded the "
                                            f"account limit")
        # Registering customer with a new account


if __name__ == '__main__':
    # acc = Account(generate_account_number(), 100.00, DataBase('mydb.db'), 'Africa/Cairo')
    # cn = acc.deposit(50.00)
    # print(acc.balance)
    # print(cn)
    # # print(cn.transaction_time_local)
    # cn = acc.localize_confirmation_number(cn)
    # print(cn)
    # print(cn.transaction_time_utc)
    # print(cn.transaction_time_local)
    # cn2 = acc.apply_interest()
    # print(cn2)
    # cn3 = acc.withdraw(15)
    # print(cn3)
    # cn4 = acc.withdraw(500)
    # print(cn4)
    # 9357044265893182
    for cn in DataBase('mydb.db').get_transactions_by_type(9357044265893182):
        print(cn)
    # print(cn.transaction_time, type(cn.transaction_time))
