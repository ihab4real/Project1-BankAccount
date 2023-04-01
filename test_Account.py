import unittest
from decimal import Decimal
from datetime import datetime
import pytz
from main import Account, TransactionDeclinedError, AccountLimitExceededError, ConfirmationNumber, \
    generate_account_number
from database import DataBase
from database_filename import get_database_filename
from unittest.mock import MagicMock


# class MockDataBase(DataBase):
#     def __init__(self):
#         super().__init__('mock.db')
#         self.transaction_id = 0
# 
#     def load_transaction_id(self):
#         return self.transaction_id
# 
#     def save_transaction_id(self, transaction_id):
#         self.transaction_id = transaction_id


class TestDeposit(unittest.TestCase):

    def setUp(self):
        self.db = DataBase(get_database_filename())
        self.mock_db = MagicMock(spec=DataBase)
        self.account = Account(generate_account_number(), 5000.00, self.mock_db)

    def test_deposit_returns_confirmation_number_object(self):
        # Act
        result = self.account.deposit(100.00)

        # Assert
        self.assertIsInstance(result, ConfirmationNumber)

    def test_balance_updated_correctly_after_successful_deposit(self):
        # Arrange
        starting_balance = self.account.balance

        # Act
        self.account.deposit(100.00)

        # Assert
        self.assertEqual(self.account.balance, starting_balance + 100)

    def test_amount_deposited_is_equal_to_amount_passed_as_argument(self):
        # Arrange
        amount = Decimal('100.00')

        # Act
        result = self.account.deposit(amount)

        # Assert
        self.assertEqual(result.amount, amount)

    def test_transaction_type_is_set_to_deposit(self):
        # Act
        result = self.account.deposit(100.00)

        # Assert
        self.assertEqual(result.transaction_type, 'D')

    def test_transaction_declined_error_raised_if_amount_passed_is_not_number_or_string_representing_number(self):
        # Act & Assert
        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit('not a number')

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit('')

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit(None)

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit({'a': 1})

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit({1, 2})

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit((1, 2))

        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit([1, 2])

    def test_deposit_valid_amount_values_rounded_to_two_decimal_places(self):
        # Define the valid deposit amounts to test
        valid_amounts = [100, 50.555, '60.98765', Decimal('40.333333333'), 0, 0.01]

        for amount in valid_amounts:
            confirmation = self.account.deposit(amount)

            # Check that the amount stored in the transaction is rounded to two decimal places
            self.assertEqual(confirmation.amount, Decimal(amount).quantize(Decimal('.01')))

    def test_transaction_is_correctly_saved_in_database(self):
        # Act
        cn = self.account.deposit(100.00)

        # Assert
        self.mock_db.add_transaction.assert_called_with(cn)

    def test_deposit_increments_transaction_id_in_database(self):
        # Get the initial transaction ID
        self.mock_db.load_transaction_id.return_value = 100

        # Act
        cn = self.account.deposit(100.00)

        self.assertEqual(self.mock_db.load_transaction_id.call_count, 1)
        self.mock_db.save_transaction_id.assert_called_once_with(101)

        # Assert
        self.mock_db.add_transaction.assert_called_once_with(cn)

    def test_deposit_transaction_type_is_X_when_TransactionDeclinedError_is_raised(self):
        # Arrange
        self.mock_db.load_transaction_id.return_value = 5

        # Act & Assert
        with self.assertRaises(TransactionDeclinedError):
            self.account.deposit('not a number')

        self.mock_db.load_transaction_id.assert_called_once()
        self.mock_db.save_transaction_id.assert_called_once_with(6)

        # self.mock_db.add_transaction.assert_called_once_with(mock_confirmation_number)
        args, kwargs = self.mock_db.add_transaction.call_args
        transaction = args[0]

        self.assertEqual(transaction.account_number, self.account.account_number)
        self.assertEqual(transaction.transaction_type, 'X')
        self.assertIsInstance(transaction.transaction_time, datetime)
        self.assertIsInstance(transaction.transaction_id, int)
        self.assertEqual(transaction.amount, Decimal('0.00'))


class TestApplyInterest(unittest.TestCase):

    def setUp(self):
        # Create a test database and banking object for each test
        self.mock_db = MagicMock(spec=DataBase)
        self.account = Account(generate_account_number(), 5000.00, self.mock_db)
        self.mock_db.load_monthly_interest_rate.return_value = Decimal('0.05')

    def test_apply_interest(self):
        # Arrange

        # Test applying interest to an account
        self.account.apply_interest()

        self.assertEqual(self.account.balance, Decimal('5250.00'))

    def test_apply_interest_returns_confirmation_number_object(self):
        # Arrange

        # Act
        result = self.account.apply_interest()

        # Assert
        self.assertIsInstance(result, ConfirmationNumber)

    def test_transaction_type_is_set_to_interest_type(self):
        # Act
        result = self.account.apply_interest()

        # Assert
        self.assertEqual(result.transaction_type, 'I')

    def test_transaction_is_correctly_saved_in_database(self):
        # Act
        cn = self.account.apply_interest()

        # Assert
        self.mock_db.add_transaction.assert_called_with(cn)

    def test_apply_interest_increments_transaction_id_in_database(self):
        # Set the transaction ID return value
        self.mock_db.load_transaction_id.return_value = 100

        # Act
        cn = self.account.apply_interest()

        # Assert
        self.mock_db.add_transaction.assert_called_once_with(cn)
        self.assertEqual(self.mock_db.load_transaction_id.call_count, 1)
        self.mock_db.save_transaction_id.assert_called_once_with(101)

    def test_apply_interest_does_not_change_balance_if_balance_is_zero(self):
        # Arrange
        acc = Account(generate_account_number(), 0, self.mock_db)

        # Act
        acc.apply_interest()

        # Assert, Verify that apply_interest does not change the balance if the balance is zero
        self.assertEqual(acc.balance, Decimal('0.00'))

    def test_apply_interest_does_not_change_balance_if_interest_rate_is_zero(self):
        # Arrange
        self.mock_db.load_monthly_interest_rate.return_value = Decimal('0.00')

        # Act
        self.account.apply_interest()

        # Assert, Verify that apply_interest does not change the balance if the interest rate is zero
        self.assertEqual(self.account.balance, Decimal('5000.00'))

        # Reset
        self.mock_db.load_monthly_interest_rate.return_value = Decimal('0.05')

    # --------------------------------------------------------
    def test_change_monthly_interest_rate_valid_input(self):
        # Act
        self.account.change_monthly_interest_rate('0.06', self.mock_db)

        # Assert
        self.assertEqual(self.account.__class__.monthly_interest_rate, Decimal('0.06'))
        self.mock_db.save_monthly_interest_rate.assert_called_once_with(Decimal('0.06'))

    def test_change_monthly_interest_rate_valid_input_with_extra_zeros(self):
        # Act
        self.account.change_monthly_interest_rate('0.06500', self.mock_db)

        # Assert
        self.assertEqual(self.account.__class__.monthly_interest_rate, Decimal('0.06'))
        self.mock_db.save_monthly_interest_rate.assert_called_once_with(Decimal('0.06'))

    def test_change_monthly_interest_rate_invalid_interest_value(self):
        # Act and Assert
        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate('invalid_interest', self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate('', self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate(None, self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate({'a': 1}, self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate({1, 2}, self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate((1, 2), self.mock_db)

        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate([1, 2], self.mock_db)

    def test_change_monthly_interest_rate_invalid_input_negative_number(self):
        # Act and Assert
        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate('-0.01', self.mock_db)

    def test_change_monthly_interest_rate_invalid_input_exceed_maximum(self):
        # Act and Assert
        with self.assertRaises(ValueError):
            self.account.change_monthly_interest_rate('0.41', self.mock_db)


class TestWithdraw(unittest.TestCase):
    def setUp(self):
        # Create a test database and account object for each test
        self.mock_db = MagicMock(spec=DataBase)
        self.account = Account(generate_account_number(), 5000.00, self.mock_db)

    def test_withdraw_successfully(self):
        # Arrange
        amount = Decimal('1000.00')
        expected_balance = Decimal('4000.00')

        # Act
        self.account.withdraw(amount)

        # Assert
        self.assertEqual(self.account.balance, expected_balance)

    def test_balance_updated_correctly_after_successful_withdraw(self):
        # Arrange
        starting_balance = self.account.balance

        # Act
        self.account.withdraw(100.00)

        # Assert
        self.assertEqual(self.account.balance, starting_balance - 100)

    def test_withdraw_returns_confirmation_number_object(self):
        # Act
        result = self.account.withdraw(100.00)

        # Assert
        self.assertIsInstance(result, ConfirmationNumber)

    def test_withdraw_amount_greater_than_balance(self):
        # Arrange
        amount = Decimal('6000.00')

        # Act & Assert
        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw(amount)

    def test_amount_withdrew_is_equal_to_amount_passed_as_argument(self):
        # Arrange
        amount = Decimal('100.00')

        # Act
        result = self.account.withdraw(amount)

        # Assert
        self.assertEqual(result.amount, amount)

    def test_transaction_type_is_set_to_withdraw(self):
        # Act
        result = self.account.withdraw(100.00)

        # Assert
        self.assertEqual(result.transaction_type, 'W')

    def test_transaction_declined_error_raised_if_amount_passed_is_not_number_or_string_representing_number(self):
        # Act & Assert
        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw('not a number')

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw('')

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw(None)

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw({'a': 1})

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw({1, 2})

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw((1, 2))

        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw([1, 2])

    def test_withdraw_valid_amount_values_rounded_to_two_decimal_places(self):
        # Define the valid deposit amounts to test
        valid_amounts = [100, 50.555, '60.98765', Decimal('40.333333333'), 0.01]

        for amount in valid_amounts:
            confirmation = self.account.withdraw(amount)

            # Check that the amount stored in the transaction is rounded to two decimal places
            self.assertEqual(confirmation.amount, Decimal(amount).quantize(Decimal('.01')))

    def test_withdraw_zero_amount(self):
        # Act & Assert
        with self.assertRaises(TransactionDeclinedError):
            self.account.withdraw(0)

    def test_transaction_is_correctly_saved_in_database(self):
        # Act
        cn = self.account.withdraw(100.00)

        # Assert
        self.mock_db.add_transaction.assert_called_with(cn)

    def test_withdraw_increments_transaction_id_in_database(self):
        # Arrange
        self.mock_db.load_transaction_id.return_value = 100

        # Act
        cn = self.account.withdraw(100.00)

        # Assert
        self.mock_db.add_transaction.assert_called_once_with(cn)
        self.assertEqual(self.mock_db.load_transaction_id.call_count, 1)
        self.mock_db.save_transaction_id.assert_called_once_with(101)

    def test_withdraw_transaction_type_is_X_when_TransactionDeclinedError_is_raised(self):
        # Arrange
        self.mock_db.load_transaction_id.return_value = 27
        test_values = ['not a number', -10, 0, 8000]

        # Act & Assert
        for test_value in test_values:
            with self.assertRaises(TransactionDeclinedError):
                self.account.withdraw(test_value)

            # Check sent confirmation number details
            args, kwargs = self.mock_db.add_transaction.call_args
            transaction = args[0]

            # Assert
            self.mock_db.save_transaction_id.assert_called_with(28)
            self.assertEqual(transaction.account_number, self.account.account_number)
            self.assertEqual(transaction.transaction_type, 'X')
            self.assertIsInstance(transaction.transaction_time, datetime)
            self.assertIsInstance(transaction.transaction_id, int)
            self.assertEqual(transaction.amount, Decimal('0.00'))

        self.assertEqual(self.mock_db.load_transaction_id.call_count, 4)
        self.assertEqual(self.mock_db.save_transaction_id.call_count, 4)

    # def test_time_zones(self):
    #     account_utc = Account("1234567890123456", 500, self.db)
    #     account_local = Account("1234567890123457", 500, self.db, "US/Eastern")
    #     account_utc.deposit(100)
    #     account_local.deposit(100)
    #     utc_time = datetime.now(tz=pytz.utc)
    #     local_time = datetime.now(tz=pytz.timezone("US/Eastern"))
    #     self.assertEqual(account_utc._transactions[0].transaction_time_utc, utc_time.isoformat())
    #     self.assertEqual(account_local._transactions[0].transaction_time_utc, utc_time.isoformat())
    #     self.assertEqual(account_utc._transactions[0].transaction_time_local,
    #                      utc_time.strftime('%Y-%m-%d %H:%M:%S (UTC+0000)'))
    #     self.assertEqual(account_local._transactions[0].transaction_time_local,
    #                      local_time.strftime('%Y-%m-%d %H:%M:%S (EDT-0400)'))
    #
    # def test_account_limit_exceeded(self):
    #     Account("1", 500, self.db)
    #     Account("2", 500, self.db)
    #     Account("3", 500, self.db)
    #     with self.assertRaises(AccountLimitExceededError):
    #         Account("4", 500, self.db)
