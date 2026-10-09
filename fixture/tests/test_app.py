import unittest
from app import add


class ArithmeticBehavior(unittest.TestCase):
    def test_positive_integers(self):
        self.assertEqual(add(2, 3), 5)

    def test_negative_integers(self):
        self.assertEqual(add(-2, 3), 1)


if __name__ == "__main__":
    unittest.main()
