import unittest
from test_Account import TestDeposit, TestApplyInterest, TestWithdraw

if __name__ == '__main__':
    suite_deposit = unittest.TestSuite()
    suite_deposit.addTest(unittest.makeSuite(TestDeposit))
    runner = unittest.TextTestRunner()
    runner.run(suite_deposit)

    # ----------------------------------------------

    suite_apply_interest = unittest.TestSuite()
    suite_apply_interest.addTest(unittest.makeSuite(TestApplyInterest))
    runner = unittest.TextTestRunner()
    runner.run(suite_apply_interest)

    # ----------------------------------------------

    suite_withdraw = unittest.TestSuite()
    suite_withdraw.addTest(unittest.makeSuite(TestWithdraw))
    runner = unittest.TextTestRunner()
    runner.run(suite_withdraw)
