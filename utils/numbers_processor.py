import re
from fractions import Fraction

class NumbersProcessor:

    #中文與數字轉換
    @staticmethod
    def chinese_to_numeric_mapping(chinese_character):
        chinese_to_numeric = {
            "一": 1, "每": 1,
            "兩": 2, "二": 2,
            "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
        }
        return chinese_to_numeric.get(chinese_character, None)

    #帶分數轉換
    @staticmethod
    def is_mixed_fraction(expression):
        tokens = re.findall(r'\d+/\d+|\d+|[+]', expression)
        if '+' in tokens:
            for token in tokens:
                if '/' in token:
                    try:
                        Fraction(token)
                        return True
                    except ValueError:
                        pass
        return False

    #判斷是不是分數
    @staticmethod
    def is_fraction_string(s):
        try:
            Fraction(s)
            return True
        except ValueError:
            return False

    #找問號
    @staticmethod
    def determine_quantity_value(quantity_value):
        tmp_value = "?"
        if NumbersProcessor.is_mixed_fraction(str(quantity_value)):
            tmp_value = quantity_value
        elif NumbersProcessor.is_fraction_string(str(quantity_value)):
            tmp_value = quantity_value
        elif str(quantity_value).isdigit():
            tmp_value = quantity_value
        elif NumbersProcessor.chinese_to_numeric_mapping(str(quantity_value)) is not None:
            tmp_value = NumbersProcessor.chinese_to_numeric_mapping(str(quantity_value))
        return tmp_value
