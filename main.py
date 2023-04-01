from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, getcontext
import secrets
import pickle
import pytz
from database import DataBase
import re


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
    def __init__(self, transaction_type, account_number, transaction_time, transaction_id, amount=Decimal('0.00')):
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
        self._amount = Decimal(value).quantize(Decimal('.01'))

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

    def __init__(self, account_number, balance, db: DataBase, time_zone='Africa/Cairo'):
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
    def change_monthly_interest_rate(cls, interest, db):
        if not cls.is_amount_a_number(interest):
            raise ValueError("Invalid interest: interest must be a number or a string representing a number")

        interest = Decimal(interest).quantize(Decimal('.01'))

        if interest < 0:
            raise ValueError("Invalid interest: interest must be a non-negative number")

        if interest > Decimal('0.4'):
            raise ValueError("Invalid interest: interest must not exceed 40%")

        db.save_monthly_interest_rate(interest)

        cls.monthly_interest_rate = interest
        print(f"Monthly interest rate updated to {cls.monthly_interest_rate}")

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

        if amount <= 0:
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError('Invalid amount: amount must be a positive number.')

        if amount > self._balance:
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError(
                'Invalid amount: cannot withdraw an amount of money higher than the balance.')

        confirmation_number.amount = amount

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
        except (InvalidOperation, TypeError, ValueError):
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
    def __init__(self, f_name, l_name, age, gender, mobile_number, address, email, national_number):
        self._f_name = f_name
        self._l_name = l_name
        self._age = age
        self._gender = gender
        self._mobile_number = mobile_number
        self._address = address
        self._email = email
        self._national_number = national_number

    @property
    def fullname(self):
        return f'{self._f_name} {self._l_name}'

    def __repr__(self):
        return f"Customer('{self._f_name}', '{self._l_name}', {self._age}, '{self._gender}', '{self._mobile_number}'," \
               f" '{self._address}', '{self._email}', '{self._national_number}')"

    def __str__(self):
        return f'''Customer Information:
-------------------
Full Name: {self._f_name} {self._l_name}
Age: {self._age}
Gender: {self._gender}
Mobile Number: {self._mobile_number}
Address: {self._address}
Email: {self._email}
National Number: {self._national_number}'''


class BankEmployee:
    def __init__(self, db: DataBase):
        self._db = db

    def register_customer(self, f_name, l_name, age, gender, mobile_number, address, email, national_number):
        # Validate input
        self.validate_input(f_name, l_name, age, gender, mobile_number, address, email, national_number)

        # Make the number 11-digit number
        if isinstance(mobile_number, int):
            mobile_number = '0' + str(mobile_number)

        # Registering customer with a new account
        self._db.add_customer(f_name, l_name, age, gender, mobile_number, address, email, national_number)

    @staticmethod
    def validate_input(f_name, l_name, age, gender, mobile_number, address, email, national_number,
                       is_new_account=False):
        if not isinstance(f_name, str) or not f_name:
            raise ValueError("First name must be a non-empty string")
        if not isinstance(l_name, str) or not l_name:
            raise ValueError("Last name must be a non-empty string")
        national_number = str(national_number)
        if not national_number.isdigit() or len(national_number) != 14:
            raise ValueError("National number must be a 14-digit string")

        if not is_new_account:
            if isinstance(age, str):
                if not age.isdigit():
                    raise ValueError("Age must be an integer or convertible to an integer")
                age = int(age)
            if not isinstance(age, int) or age < 18:
                raise ValueError("Age must be an integer greater than or equal to 18")
            if gender not in ["Male", "Female", "Other"]:
                raise ValueError("Gender must be one of 'Male', 'Female', 'Other'")
            if isinstance(mobile_number, int):
                if len(str(mobile_number)) != 10 or str(mobile_number)[0] == '0':
                    raise ValueError(
                        "Mobile number as an integer must have 10 digits and the leftmost digit must not be zero")
            elif isinstance(mobile_number, str):
                if not mobile_number.isdigit() or len(mobile_number) != 11 or mobile_number[0] != '0' \
                        or mobile_number[1] == '0':
                    raise ValueError(
                        "Mobile number as a string must have 11 digits and start with a zero followed by"
                        " a non-zero digit")
            else:
                raise ValueError("Mobile number must be either an integer or a string")
            if not isinstance(address, str) or not address:
                raise ValueError("Address must be a non-empty string")
            if not isinstance(email, str) or not email:
                raise ValueError("Email must be a non-empty string")
            email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
            if not email_regex.match(email):
                raise ValueError("Email must be a valid email address")

    def register_new_account(self, f_name, l_name, national_number):
        # validate arguments values
        self.validate_input(f_name, l_name, None, None, None, None, None, national_number, is_new_account=True)

        # Check if customer is already in the system
        flag, customer = self._db.is_customer_in_the_system(national_number)

        # If the customer already exists, go ahead and create the account
        if flag:
            # Check if customer has already reached the accounts limit they can have (3 accounts per user)
            if not self._db.can_customer_have_another_account(national_number):
                raise AccountLimitExceededError(f"Customer with national number {national_number} has exceeded the "
                                                f"account limit")

        else:
            print(f"Hi {f_name}!. Welcome to our registration form! To continue, "
                  "we need you to provide some more information about yourself.")
            age = input("Age: ")
            gender = input("Gender: ")
            mobile_number = input("Mobile Number: ")
            address = input("Address: ")
            email = input("Email: ")
            self.register_customer(f_name, l_name, age, gender, mobile_number, address, email, national_number)

        # Create the account
        customer_id = customer[0]
        starting_balance = input('Enter a starting balance >= 1000.00 EGP: ')
        preferred_timezone = input('Enter your preferred time zone: ')
        new_account = Account(generate_account_number(), starting_balance, self._db, preferred_timezone)
        self._db.add_account(new_account, customer_id)


if __name__ == '__main__':
    ...
