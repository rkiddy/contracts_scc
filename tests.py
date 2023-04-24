
import unittest
import data

class TestData(unittest.TestCase):

    def test_year_value_for_contract(self):

        # this should be 6 days that evenly cross a year boundary.
        c = {
            'effective_date': '2022-12-29',
            'expir_date': '2023-01-03',
            'contract_value': 1000
        }

        assert data.year_value_for_contract(c, '2022') == 500
        assert data.year_value_for_contract(c, '2023') == 500

        c = {
            'effective_date': '2022-12-01',
            'expir_date': '2022-12-10',
            'contract_value': 1000
        }

        assert data.year_value_for_contract(c, '2022') == 1000
        assert data.year_value_for_contract(c, '2023') == 0
        assert data.year_value_for_contract(c, '2021') == 0

        c = {
            'effective_date': '2022-01-01',
            'expir_date': '2022-12-31',
            'contract_value': 1000
        }

        assert data.year_value_for_contract(c, '2022') == 1000
        assert data.year_value_for_contract(c, '2023') == 0
        assert data.year_value_for_contract(c, '2021') == 0

        c = {
            'effective_date': '2021-12-30',
            'expir_date': '2023-01-02',
            'contract_value': 36900
        }

        assert data.year_value_for_contract(c, '2021') == 200
        assert data.year_value_for_contract(c, '2022') == 36500
        assert data.year_value_for_contract(c, '2023') == 200


    def test_money(self):

        assert data.money(100) == '$1.00'
        assert data.money(100000) == '$1,000.00'
        assert data.money(123456) == '$1,234.56'


    def test_cost_labels(self):

        assert data.cost_labels(0) == 'B0'
        assert data.cost_labels(100000000) == 'B9'


    def test_collapse_values_normal(self):

        lines = [
            '2019-11 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2019-12 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2020-06 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2020-08 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2020-09 ARIBA INC 2014-09-01 2021-08-31 1412125350',
            '2020-10 ARIBA INC 2014-09-01 2021-08-31 1412125350',
            '2020-11 ARIBA INC 2014-09-01 2021-08-31 1412125350',
            '2022-04 ARIBA INC 2014-09-01 2022-08-31 1549125350',
            '2022-06 ARIBA INC 2014-09-01 2022-08-31 1549125350',
            '2022-07 ARIBA INC 2014-09-01 2022-08-31 1549125350',
            '2022-08 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2022-09 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2022-10 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2022-11 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2023-01 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2023-02 ARIBA INC 2014-09-01 2025-08-31 2092559800',
            '2023-03 ARIBA INC 2014-09-01 2025-08-31 2092559800']

        expected = [
                '2019-11 to 2020-08 - ARIBA INC - 2014-09-01 - 2020-08-31 - $11,949,048.00',
                '2020-09 to 2020-11 - ARIBA INC - 2014-09-01 - 2021-08-31 - $14,121,253.50',
                '2022-04 to 2022-07 - ARIBA INC - 2014-09-01 - 2022-08-31 - $15,491,253.50',
                '2022-08 to 2023-03 - ARIBA INC - 2014-09-01 - 2025-08-31 - $20,925,598.00'
        ]

        result = data.collapse_values(lines)

        self.assertEqual(expected, result)


    def test_collapse_values_minimal(self):

        lines = [
            '2019-11 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2019-12 ARIBA INC 2014-09-01 2020-08-31 1194904800',
            '2020-06 ARIBA INC 2014-09-01 2020-08-31 1194904800']

        expected = [
                '2019-11 to 2020-06 - ARIBA INC - 2014-09-01 - 2020-08-31 - $11,949,048.00'
        ]

        result = data.collapse_values(lines)

        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
