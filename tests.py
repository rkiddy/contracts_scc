
import data


def test_year_value_for_contract():

    c = {
        'effective_date': '2022-07-25',
        'expir_date': '2023-06-30',
        'contract_value': 58250000
    }

    result = data.year_value_for_contract(c)
    print(f"result: {result}")


if __name__ == '__main__':
    test_year_value_for_contract()
