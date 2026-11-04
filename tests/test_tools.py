import json
import unittest
from copy import deepcopy

from agent.tools import ORDERS, get_order


class OrderPrivacyTests(unittest.TestCase):
    def test_all_orders_hide_private_fields_without_mutating_fixtures(self):
        original = deepcopy(ORDERS)
        for order_id, order in ORDERS.items():
            with self.subTest(order_id=order_id):
                result = json.loads(get_order(order_id))
                self.assertNotIn("customer_name", result)
                self.assertNotIn("address", result)
                self.assertEqual(result, {key: value for key, value in order.items()
                                          if key not in {"customer_name", "address"}})
        self.assertEqual(ORDERS, original)

    def test_order_id_normalization_and_not_found_are_preserved(self):
        self.assertEqual(json.loads(get_order(" pp-1003 "))["order_id"], "PP-1003")
        self.assertEqual(get_order("PP-9999"), "No order found with ID PP-9999.")
