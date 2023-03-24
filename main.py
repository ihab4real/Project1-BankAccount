from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from numbers import Real


class TransactionDeclinedError(Exception):
    pass


class ConfirmationNumber:
    def __init__(self, transaction_type, account_number, transaction_time, transaction_id):
        self._transaction_type = transaction_type
        self._account_number = account_number
        self._transaction_time = transaction_time
        self._transaction_id = transaction_id


class Account:
    monthly_interest_rate = Decimal('0.5')
    transaction_id = 0

    def __init__(self, account_number, balance, time_zone):
        self._account_number = account_number
        self._time_zone = time_zone
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

    def deposit(self, amount):
        confirmation_number = ConfirmationNumber(transaction_type=self._deposit_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self.__class__.transaction_id)
        self.__class__.transaction_id += 1

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
                                                 transaction_id=self.__class__.transaction_id)
        self.__class__.transaction_id += 1

        interest = self._balance * self.monthly_interest_rate
        self._balance += interest
        print(f"Applied {self.monthly_interest_rate * 100}% interest. New balance is {self._balance}")
        self._transactions.append(confirmation_number)

    def withdraw(self, amount):
        confirmation_number = ConfirmationNumber(transaction_type=self._withdrawal_type,
                                                 account_number=self._account_number,
                                                 transaction_time=datetime.now(timezone.utc),
                                                 transaction_id=self.__class__.transaction_id)
        self.__class__.transaction_id += 1

        if not self.is_amount_a_number(amount):
            self._transaction_failure(confirmation_number)
            raise TransactionDeclinedError("Invalid amount: amount must be a number or a string representing a number.")

        amount = Decimal(amount).quantize(Decimal('.01'))

        if amount <= 0:
            self._transaction_failure(confirmation_number)
            TransactionDeclinedError('Invalid amount: amount must be a positive number.')

        if amount > self._balance:
            self._transaction_failure(confirmation_number)
            TransactionDeclinedError('Invalid amount: cannot withdraw an amount of money higher than the balance.')

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


class Customer:
    def __init__(self, f_name, l_name, account):
        self.f_name = f_name
        self.l_name = l_name
        self._account = account

    @property
    def fullname(self):
        return f'{self.f_name} {self.l_name}'


if __name__ == '__main__':
    x = 0.3
    print(x)
    print(format(x, '.18f'))
    x = Decimal(x).quantize(Decimal('.01'))
    print(x)
    print(format(x, '.28f'))
