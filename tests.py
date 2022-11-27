
import data


def test_year_value_for_contract():

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

    assert data.year_value_for_contract(c, '2022') == 36500


def test_money():

    assert data.money(100) == '$ 1.00'
    assert data.money(100000) == '$ 1,000.00'
    assert data.money(123456) == '$ 1,234.56'


def test_cost_labels():

    assert data.cost_labels(0) == 'B0'
    assert data.cost_labels(100000000) == 'B9'
