import re
from fractions import Fraction
from utils.numbers_processor import NumbersProcessor


class IASL_Solver:
    def __init__(self):
        self.variable_list = ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9", "X10",
                              "X11", "X12", "X13", "X14", "X15", "X16", "X17", "X18", "X19", "X20"]
        self.variable_index = 0
        with open('knowledge/variance_verb_plus.txt', 'r', encoding='utf-8') as file:
            self.variance_verb_plus = file.read().splitlines()

        with open('knowledge/buy_verbs.txt', 'r', encoding='utf-8') as file:
            self.buy_verbs = file.read().splitlines()

    def fill_in_parameters(self, value, unit, entity, meaning=None, sentence=None, clue=None, verb=None, subject=None, object=None):
        return {
            'value': value,
            'unit': unit,
            'entity': entity,
            'meaning': meaning,
            'sentence': sentence,
            'clue': clue,
            'verb': verb,
            'subject': subject,
            'object': object
        }
    
    def process_data(self, extracted_data):
    
        self.variable_index = 0
        output = {
            "QuestionID": extracted_data['qid'],
            "Variable": {},
            "stype": extracted_data['stype'],
            "Description": "",
            "Formula": "",
            "Answer": extracted_data["answer"]
        }

        for key, quantities in extracted_data['quantities'].items():
            for quantity in quantities:
                if self.variable_index < len(self.variable_list):
                    variable_name = self.variable_list[self.variable_index]
                    quantity['quantity']['value'] = NumbersProcessor.determine_quantity_value(quantity['quantity']['value'])

                    output["Variable"][variable_name] = {
                        'value': quantity['quantity']['value'],
                        'unit': quantity['quantity']['unit'],
                        'entity': quantity['quantity'].get('entity', None),
                        'sentence': key,
                        'clue': None,
                        'verb': quantity.get('verb', None),
                        'subject': quantity.get('subject', None),
                        'object': quantity.get('object', None),
                    }
                    self.variable_index += 1
        return output

    # 以下合成單位量
    def unitmap_to_formula(self, input_data, sentence):
        variables = input_data['Variable']
        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]

        def determine_larger_smaller(key1, key2):
            value1 = float(variables[key1]['value'])
            value2 = float(variables[key2]['value'])

            if value1 == 1.0:
                return key2, value2, key1, value1
            elif value2 == 1.0:
                return key1, value1, key2, value2
            else:
                return (key1, value1, key2, value2) if value1 > value2 else (key2, value2, key1, value1)

        occurrence_counter = 1
        matching_vars = [k for k, v in variables.items() if v['sentence'] == sentence]

        if len(matching_vars) < 2:
            print(f"Not enough variables found for sentence {sentence}. Expected 2, found {len(matching_vars)}.")
            return input_data

        x_key1, x_key2 = matching_vars[:2]
        if x_key1 in variables and x_key2 in variables:
            larger_key, larger_value, smaller_key, smaller_value = determine_larger_smaller(x_key1, x_key2)

            new_variable = unused_variables.pop(0)
            unit_larger = variables[larger_key]['unit']
            unit_smaller = variables[smaller_key]['unit']
            new_value = larger_value / smaller_value
            new_unit = f"{unit_larger}/{unit_smaller}"

            variables[new_variable] = {
                'value': new_value,
                'unit': new_unit,
                'entity': f"{variables[larger_key]['entity']}/{variables[smaller_key]['entity']}",
                'meaning': None,
                'sentence': f'{sentence}-{occurrence_counter}',
                'clue': "單位量"
            }
            occurrence_counter += 1

            X1v = round(float(variables[x_key1]['value']), 2)
            X2v = round(float(variables[x_key2]['value']), 2)
            Nv = round(float(new_value), 2)

            input_data['Description'] += (f"Unitmap Scan: {sentence} 有兩個單位，"
                                        f"{X1v}{variables[x_key1]['unit']},"
                                        f"{X2v}{variables[x_key2]['unit']}，"
                                        f"合併成一個單位量{Nv}{new_unit} 。  ")
        else:
            print(f"Expected variables {x_key1} and {x_key2} not found.")

        return input_data

    def process_unitmap(self, input_data):
        stype = input_data['stype']

        for index, type_phrase in enumerate(stype):
            if type_phrase == "每單位量":
                relevant_sentence = f"s{index + 1}"
                input_data = self.unitmap_to_formula(input_data, relevant_sentence)

        return input_data
    

    #以下是量變，針對已有物品針對此物品做增減，如(有100顆蘋果，爛了3顆) 的爛

    def adjust_object_variance(self, input_data, subject=None, entity=None, clue=None):
        stype = input_data['stype']

        for index, type_phrase in enumerate(stype):
            if type_phrase == "量變":
                # print("Here")
                relevant_sentence = f"s{index + 1}"
                input_data = self.adjust_object_variance_to_formula(input_data, relevant_sentence, subject, entity, clue)
                
        return input_data

    def adjust_object_left(self, input_data, subject=None, entity=None, clue=None):
        stype = input_data['stype']

        for index, type_phrase in enumerate(stype):
            if type_phrase == "剩下":
                # print("Here")
                relevant_sentence = f"s{index + 1}"
                input_data = self.adjust_object_variance_to_formula(input_data, relevant_sentence, subject, entity, clue)
                
        return input_data

    def adjust_object_variance_to_formula(self, input_data, sentence, subject=None, entity=None, clue=None):
        variables = input_data['Variable']
        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]

        # Find the var_variable based on the sentence
        var_variable = None
        for key, value in variables.items():
            if value['sentence'] == sentence:
                var_variable = value
                var_variable_key = key
                break

        if var_variable is None:
            raise ValueError("No variable found in the target sentence.")

        # Find the target_variable based on subject, entity, and clue
        def match_criteria(value):
            return ((subject is None or value['subject'] == subject) and
                    (entity is None or value['entity'] == entity) and
                    (clue is None or value['clue'] == clue))

        target_variable = None
        for key, value in variables.items():
            if match_criteria(value):
                target_variable = value
                break

        if target_variable is None:
            raise ValueError("No variable found matching the given criteria.")

        if target_variable['entity'] != var_variable['entity']:
            return input_data 

        if var_variable['verb'] in self.variance_verb_plus:
            k = float(target_variable['value']) + float(var_variable['value'])
            input_data['Formula'] += " + "
        else:
            k = float(target_variable['value']) - float(var_variable['value'])
            input_data['Formula'] += " - "
        new_variable_key = unused_variables.pop(0)
      
        new_variable = self.fill_in_parameters(value=k,unit=target_variable['unit'],entity=target_variable['entity'],meaning=None,sentence=var_variable['sentence'],clue='可分配物')
        # Update the target variable's clue
        target_variable['clue'] = '原分配物'
        v1v = target_variable['value']
        v1u = target_variable['unit']
        v1e = target_variable['entity']
        v2v = var_variable['value']

        input_data['Description'] += (f"這裡我們計算實際的分配數量，原有{v1v}{v1u}{v1e}，出現量變，"
                                    f"觀察到動詞為{var_variable['verb']}，可以推得這是做一個-的運算。"
                                    f"因此{v1v}-{v2v}={k}，為更新後實際能分配的數量")
        # Add new variable to input_data
        input_data['Variable'][new_variable_key] = new_variable
        input_data['Formula'] += v2v
        input_data['Formula']  = self.add_parentheses( input_data['Formula'])

        return input_data
    
    #把每個元標記起來 如24 元 蘋果
    def tag_item_price(self, input_data):
        for key, variable in input_data['Variable'].items():
            if variable['unit'] == '元' and variable['value'] != '?' and variable['clue'] == None:
                variable['clue'] = '單位價格'
                input_data['Description'] += f"{variable['entity']}{variable['value']}元為單位價格。"

        
        return input_data
    
    # 如果動詞有買，如果有錢，計算相對應購買的價格
    def calculate_bought_item_price(self, input_data):
        target_items = []
        new_variables = []

        # Step 1: Find the target items
        for key, variable in input_data['Variable'].items():
            if variable['verb'] in self.buy_verbs and variable['clue'] is None:
                target_items.append((key, variable))

        # Step 2: Match target items with corresponding unit price variables
        input_data["Description"] += f"將購買的量與單位價格相乘得到應付價格。"
        for target_key, target_variable in target_items:
            if target_variable['clue'] != None:
                continue
            
            target_entity = target_variable['entity']
            target_value = target_variable['value']
            target_unit = target_variable['unit']

            for key, variable in input_data['Variable'].items():
                if variable['entity'] == target_entity and variable['clue'] == '單位價格':
                    unit_price_value = variable['value']
                    # Step 3: Calculate the total price
                    total_price = int(target_value) * int(unit_price_value)

                    # Step 4: Add a new variable for the calculated total price
                    new_variable_name = self.variable_list[self.variable_index]
                    self.variable_index += 1

                    new_variable = {
                        'value': total_price,
                        'unit': "元",
                        'entity': target_entity,
                        'sentence': target_variable['sentence'],
                        'clue': "已買價格",
                        'verb': target_variable['verb'],
                        'subject': None,
                        'object': None
                    }
                    new_variables.append((new_variable_name, new_variable))
                    input_data["Description"] += f"{target_value}{target_unit}{target_entity} * {unit_price_value} = {total_price} (應付價格)。"
                    break

        # Add all new variables to the input data after iteration
        for new_variable_name, new_variable in new_variables:
            input_data['Variable'][new_variable_name] = new_variable

        return input_data
    
    def convert_mixed_fractions(self,data):
        def convert_value(value):
            if isinstance(value, str) and '+' in value:
                match = re.match(r'(\d+)\+\((\d+)/(\d+)\)(\D*)', value)
                if match:
                    whole, num, denom, unit = match.groups()
                    whole = int(whole)
                    frac = Fraction(int(num), int(denom))
                    result = Fraction(whole) + frac
                    return f"{result.numerator}/{result.denominator}{unit}"
            return value

        for var in data['Variable'].values():
            var['value'] = convert_value(var['value'])

        data['Answer'] = convert_value(data['Answer'])
        
        return data
    
    def format_fractions(self,fractions_list):
        formatted_fractions = []
        for frac in fractions_list:
            if isinstance(frac, Fraction):
                formatted_fractions.append(f"{frac.numerator}/{frac.denominator}")
            elif isinstance(frac, tuple):
                if frac[1] == 1:
                    formatted_fractions.append(f"{frac[0]}")
                else:
                    formatted_fractions.append(f"{frac[0]}/{frac[1]}")
        return formatted_fractions
    
    def mixed_to_improper(self,mixed_str):
        if '+' in mixed_str:
            whole, fraction = mixed_str.split('+')
            whole = int(whole)
            num, denom = map(int, fraction.strip('()').split('/'))
            return Fraction(whole * denom + num, denom)
        else:
            return Fraction(mixed_str)

    # 以下
    
    def add_parentheses(self,input_string):
        return f"({input_string})"

    def check_two_questions(self, data):
        stype = data['stype']
        if len(stype) >= 2 and stype[-2].startswith('問') and stype[-1].startswith('問'):
            return True

    def eval_data(self, extracted_data):
        if extracted_data['Question Type'] == "Single":
            my_answer = extracted_data['My Answer']
            solution = extracted_data['Solution']
            solution = re.sub(r'[^\d.]', '', solution)
            try:
                solution = float(solution)
                solution = round(solution, 1)
            except ValueError:
                return False

            return float(my_answer) == solution
        else:
            solution = extracted_data['Solution']
            solution = self.extract_two_answers(solution)
            my_answer = self.parse_my_answer(extracted_data['My Answer'])
            return solution == my_answer


            
    def extract_two_answers(self, s):
        # Split the input string by semicolon
        parts = s.split(';')
        # Use regular expression to find numbers in each part
        numbers = [round(float(re.search(r'[0-9.]+', part).group()), 2) for part in parts]
        # Convert the list of numbers to a tuple
        return tuple(numbers)
    
    def parse_my_answer(self, s):
        # Remove parentheses and split by comma
        s = s.strip('()')
        parts = s.split(',')
        # Convert parts to float and round to two decimal places
        numbers = [round(float(part), 2) for part in parts]
        return tuple(numbers)