from .iasl_solver import IASL_Solver
from fractions import Fraction
import ast

import re

class Unitmap_Solver(IASL_Solver):

    def process_data(self, extracted_data):
        output = super().process_data(extracted_data)
        output["分子"] = None
        output["分母"] = None
        output['target_分子_unit'] = ""
        output['target_分母_unit'] = ""
        output['target_分子_entity'] = None
        output['target_分母_entity'] = None
        output['target_entity'] = None
        output['target_unit'] = None
        output['matched_clue'] = None
        output["分配物值"] = None
        output["分配量"] = None
        output['ratio'] = None
        output['fraction_value'] = None

        return output
    
    # 找到問句問的單位量
    def find_asked_unitmap(self,input_data):
        output = input_data.copy()

        # Step 1: Find the index of "問單位量" in stype
        target_index = output['stype'].index('問單位量')
        target_sentence = f's{target_index + 1}'

        # Step 2: Find the first two Variables with the target sentence
        variables_in_target_sentence = [k for k, v in output['Variable'].items() if v['sentence'] == target_sentence]
        if len(variables_in_target_sentence) < 2:
            raise ValueError("Not enough variables in target sentence")

        # Step 3: Identify 分子 and 分母
        分子 = 分母 = None
        for var in variables_in_target_sentence:
            if output['Variable'][var]['value'] == '?':
                分子 = var
            else:
                分母 = var

        if 分子 is None or 分母 is None:
            raise ValueError("Unable to determine 分子 or 分母")

        output['分子'] = 分子
        output['分母'] = 分母

        # Step 4: Create a new Variable with the ratio
        if self.variable_index < len(self.variable_list):
            new_variable = self.variable_list[self.variable_index]
            self.variable_index += 1
        else:
            raise ValueError("No available variable names left")

        分母_value = output['Variable'][分母]['value']
        分母_unit = output['Variable'][分母]['unit']
        分子_unit = output['Variable'][分子]['unit']
        分母_entity = output['Variable'][分母]['entity']
        分子_entity = output['Variable'][分子]['entity']

        output["Variable"][new_variable] = {
            'value': "unknown",
            'unit': f"{分子_unit}/{分母_unit}",
            'entity': f"{分子_entity}/{分母_entity}",
            'sentence': "question",
            'clue': "asked_variable",
            'ratio': 分母_value
        }
        output['target_分子_unit'] = 分子_unit
        output['target_分母_unit'] = 分母_unit
        output['target_分子_entity'] = 分子_entity
        output['target_分母_entity'] = 分母_entity
        output['target_entity'] = f"{分子_entity}/{分母_entity}"
        output['target_unit'] = f"{分子_unit}/{分母_unit}"
        output['Description'] += f"此題為問單位量相關問題。首先觀察問句，需求得{分子_entity}在{分母_value}{分母_unit}{分母_entity}時對應為多少{分子_unit}。"

        output['ratio'] = 分母_value
        
        return output
        
    def determine_larger_smaller(self, key1, key2, variables, target_entity, target_unit):
        entity1 = variables[key1]['entity']
        entity2 = variables[key2]['entity']
        unit1 = variables[key1]['unit']
        unit2 = variables[key2]['unit']

        if entity1 == target_entity and unit1 == target_unit:
            return key1, Fraction(variables[key1]['value']), key2, Fraction(variables[key2]['value'])
        elif entity2 == target_entity and unit2 == target_unit:
            return key2, Fraction(variables[key2]['value']), key1, Fraction(variables[key1]['value'])
        else:
            value1 = Fraction(variables[key1]['value'])
            value2 = Fraction(variables[key2]['value'])
            return (key1, value1, key2, value2) if value1 > value2 else (key2, value2, key1, value1)

    def unitmap_to_formula(self, input_data, sentence):
        variables = input_data['Variable']
        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]

        occurrence_counter = 1
        matching_vars = [k for k, v in variables.items() if v['sentence'] == sentence]

        if len(matching_vars) < 2:
            print(f"Not enough variables found for sentence {sentence}. Expected 2, found {len(matching_vars)}.")
            return input_data

        x_key1, x_key2 = matching_vars[:2]
        if x_key1 in variables and x_key2 in variables:
            larger_key, larger_value, smaller_key, smaller_value = self.determine_larger_smaller(
                x_key1, x_key2, variables,
                input_data['target_分子_entity'], input_data['target_分子_unit']
            )

            new_variable = unused_variables.pop(0)
            unit_larger = variables[larger_key]['unit']
            unit_smaller = variables[smaller_key]['unit']
            new_value = Fraction(larger_value / smaller_value)
            new_unit = f"{unit_larger}/{unit_smaller}"
            new_entity = f"{variables[larger_key]['entity']}/{variables[smaller_key]['entity']}"


            variables[new_variable] = {
                'value': new_value,
                'unit': new_unit,
                'entity': new_entity,
                'meaning': None,
                'sentence': f'{sentence}-{occurrence_counter}',
                'clue': "單位量"
            }
            occurrence_counter += 1

            X1v = round(float(Fraction(variables[x_key1]['value'])),2)
            X2v = round(float(Fraction(variables[x_key2]['value'])),2)
            input_data['Description'] += (f" {sentence} 有兩個單位，"
                                        f"{variables[x_key1]['value']}{variables[x_key1]['unit']},"
                                        f"{variables[x_key2]['value']}{variables[x_key2]['unit']}，透過'{variables[x_key1]['verb']}'的存在比例關係。"
                                        f"將兩單位合併成一個單位量{new_value} ({new_unit})。")

            if new_entity == input_data['target_entity'] and new_unit == input_data['target_unit']:
                input_data['matched_clue'] = new_variable
                input_data['Description'] += f"此合成的新單位量與問句求的({new_unit})一致。"
                input_data['fraction_value'] = new_value
                print("herre")

            # Nv = float(new_value)

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
    
    def process_portion_scan(self, input_data):
        if input_data['matched_clue'] is not None:
            return input_data
        
        input_data['Description'] += f"題意無直接對應到的單位量線索，需跨句組合來找出線索。我們需分別找到 分子: {input_data['target_分子_entity']}的{input_data['target_分子_unit']}數 及 分母:{input_data['target_分母_entity']}{input_data['target_分母_unit']}數。"
        
        for i in range(0, len(input_data['stype'])):
            if input_data['stype'][i] == "平分":
                # Identify the sentence corresponding to the next index after the current "平分" index
                target_sentence = 's' + str(i + 1)
                # Search for the variable that uses this sentence
                for variable, details in input_data['Variable'].items():
                    if details['sentence'] == target_sentence:
                        # If found, add "單位量" to the clue of this variable
                        # input_data['Variable'][variable]['clue'] = '單位量'
                        v = input_data['Variable'][variable]['value']
                        e = input_data['Variable'][variable]['entity']
                        u  = input_data['Variable'][variable]['unit']

                        if e == input_data['target_分母_entity'] and u  == input_data['target_分母_unit']:
                            input_data["分配量"] = v
                            input_data['Description'] += f"題意出現({v}{u}{e})與問句所求一致，{v}為此題的分母單位。 "
                
        return input_data

    def process_left(self, input_data):
    # 1. If '分配物值' is None, return the original data
        if input_data.get('分配物值') is None:
            return input_data

    # 2. Check for both '剩下' and '找回' in stype
        target_types = ['剩下', '找回']
        for target_type in target_types:
            try:
                type_index = input_data['stype'].index(target_type)
                target_sentence = f's{type_index + 1}'

            # 3. Iterate through the variables
                for var in input_data['Variable'].values():
                    if var['sentence'] == target_sentence:
                    # 4. Check if unit and entity match
                        if (var['unit'] == input_data['target_分子_unit'] or var['unit'] == 'used') and \
                           (var['entity'] == input_data['target_分子_entity'] or var['entity'] is None):
                        # Subtract the variable's value from 分配物值

                            original_value = Fraction(input_data['分配物值'])
                            subtracted_value = Fraction(var['value'])
                            new_value = original_value - subtracted_value
                            input_data["Formula"] += f" - {new_value}"
                            # input_data["Formula"] = self.add_parentheses(input_data["Formula"])

                        # Update 分配物值
                            input_data['分配物值'] = str(new_value)
                            break  # Exit the loop after processing

            except ValueError:
                continue  # If the target_type is not in stype, continue to the next type

        return input_data

 
    
    def safe_eval(self,value):
        if isinstance(value, (int, float, Fraction)):
            return value
        elif isinstance(value, str):
            try:
                return eval(value)
            except:
                return float(value)
        else:
            raise ValueError(f"Unexpected type for value: {type(value)}")

    # 把分配物值和分配量合併成單位量
    def mixed_unitmap(self,input_data):
        if input_data['matched_clue'] is not None:
            return input_data
        variables = input_data['Variable']
        # unused_variables = [f'X{i}' for i in range(6, 10)]  # Assuming X1-X5 are used
        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]
        
        # Find the '分配物值' and '分配量'
        # print(input_data['分配物值'])
        # print(input_data['分配量'])
        if input_data['分配物值'] is None:
            return input_data
        if input_data['分配量'] is None:
            return input_data
        distribute_value = float(self.safe_eval(input_data['分配物值']))
        # distribute_value = float(eval(input_data['分配物值']))
        distribute_amount = float(self.safe_eval(input_data['分配量']))
        
        # Calculate the new value
        new_value = Fraction(distribute_value / distribute_amount).limit_denominator()
        
        # Create the new variable
        
        new_variable = unused_variables.pop(0)
        
        variables[new_variable] = {
            'value': str(new_value),
            'unit': input_data['target_unit'],
            'entity': input_data['target_entity'],
            'meaning': None,
            'sentence': 'new',
            'clue': "單位量"
        }
        
        # Update the matched_clue
        input_data['matched_clue'] = new_variable
        input_data['Description'] += f"將跨句收集到的分子單位與分母單位組合成一個新的單位量。{distribute_value}/{distribute_amount} = {str(new_value)} ({input_data['target_unit']})。"
        input_data['fraction_value'] += f" / {distribute_amount}"
    
        return input_data
    


    # from fractions import Fraction
    # 相乘
    def variance_map_unitmap(self, input_data):
        if input_data['matched_clue'] is not None:
            return input_data

        variables = input_data['Variable']
        stype = input_data['stype']

        try:
            quantity_change_index = stype.index('量變')
        except ValueError:
            return input_data

        target_sentence = f's{quantity_change_index + 1}'

        target_variable = None
        for var, details in variables.items():
            if details['sentence'] == target_sentence:
                target_variable = details
                break

        if not target_variable:
            return input_data

        target_entity = target_variable['entity']
        target_unit = target_variable['unit']

        unitmap_variable = None
        for var, details in variables.items():
            if details['clue'] == '單位量':
                entity_parts = details['entity'].split('/')
                unit_parts = details['unit'].split('/')
                if (len(entity_parts) > 1 and len(unit_parts) > 1 and
                    entity_parts[1] == target_entity and
                    unit_parts[1] == target_unit):
                    unitmap_variable = details
                    break

        if not unitmap_variable:
            return input_data

        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]
        new_variable = unused_variables.pop(0)

        new_value = Fraction(target_variable['value']) * unitmap_variable['value']

        variables[new_variable] = {
            'value': new_value,
            'unit': target_variable['unit'],
            'entity': target_variable['entity'],
            'meaning': None,
            'sentence': '',
            'clue': ''
        }
        input_data['Description'] += f"在題目裡出現{target_variable['value']}{target_variable['unit']}{target_variable['entity']} 和 {unitmap_variable['value']}({unitmap_variable['unit']})的單位量。"
        input_data['Description'] += f"我們將他相乘。得到{target_variable['value']}*{unitmap_variable['value']}={new_value}。"
        input_data['Description'] += f"{new_value}{input_data['target_分子_unit']}{ target_variable['entity']}為分子單位。"

        input_data['Variable'] = variables
        input_data['分配物值'] = new_value

        return input_data
    
    def combined_unitmaps(self, input_data):
        variables = input_data['Variable']
        
        # Step 1: Extract variables with clue == "單位量"
        unit_vars = {k: v for k, v in variables.items() if v.get('clue') == '單位量'}
        new_value = 0
        new_unit = ""
        
        if len(unit_vars) == 2:
            var1, var2 = list(unit_vars.values())
            
            # Step 2 and 3: Retrieve and split units
            unit1 = var1['unit'].split('/')
            unit2 = var2['unit'].split('/')
            
            if len(unit1) == 2 and len(unit2) == 2 and unit1[1] == unit2[0]:
                # Step 4 and 5: Create new variable X20
                new_value = var1['value'] * var2['value']
                new_unit = f"{unit1[0]}/{unit2[1]}"
                
                variables['X20'] = {
                    'value': new_value,
                    'unit': new_unit,
                    'entity': var1['entity'],
                    'meaning': None,
                    'clue': "新單位量"
                }


        
        # Step 6: Return the modified data
                input_data['Variable'] = variables
                if new_unit == input_data['target_unit']:
                    input_data['matched_clue'] = "X20"
                    # input_data['Description'] += "觀察到"
                    
            if len(unit1) == 2 and len(unit2) == 2 and unit1[0] == unit2[1]:
                # Step 4 and 5: Create new variable X20
                new_value = var1['value'] * var2['value']
                # new_unit = f"{unit1[1]}/{unit2[0]}"
                new_unit = f"{unit2[0]}/{unit1[1]}"

                
                variables['X20'] = {
                    'value': new_value,
                    'unit': new_unit,
                    'entity': var1['entity'],
                    'meaning': None,
                    'clue': "新單位量"
                }
        
        # Step 6: Return the modified data
                input_data['Variable'] = variables
                if new_unit == input_data['target_unit']:
                    input_data['matched_clue'] = "X20"

            if len(unit1) == 2 and len(unit2) == 2 and unit1[1] == unit2[1]:
                # Step 4 and 5: Create new variable X20
                new_value = Fraction(var1['value']) / Fraction(var2['value'])
                # new_unit = f"{unit1[1]}/{unit2[0]}"
                new_unit = f"{unit1[0]}/{unit2[0]}"

                
                variables['X20'] = {
                    'value': new_value,
                    'unit': new_unit,
                    'entity': var1['entity'],
                    'meaning': None,
                    'clue': "新單位量"
                }
        
        # Step 6: Return the modified data
                input_data['Variable'] = variables
                if new_unit == input_data['target_unit']:
                    input_data['matched_clue'] = "X20"
            input_data['Description']+=f"將前面兩個單位量，{var1['value']}、{var2['value']}串聯，可以得到新的單位量{new_value}({new_unit})。 "

        return input_data


    def track_variable_value(self, input_data):
    # Step 1: Check if '分配物值' is None
        if input_data.get('分配物值') is None:
            return input_data

        # Step 2: Find target sentences
        target_sentences = []
        for i, stype in enumerate(input_data.get('stype', [])):
            if stype == '量變':
                target_sentences.append(f's{i+1}')

        if not target_sentences:
            return input_data

        # Step 3-5: Iterate through variables and update '分配物值'
        分配物值 = Fraction(input_data['分配物值'])
        original_value = 分配物值  # Store the original value

        for var in input_data.get('Variable', {}).values():
            if var['sentence'] in target_sentences:
                if (var['unit'] == input_data.get('target_分子_unit') and 
                    var['entity'] == input_data.get('target_分子_entity') and
                    not var.get('is_original', False)):
                    k = 分配物值 -float(var['value'])
                    input_data['Description'] += f"觀察到題目中出現{var['verb']}{var['value']}{var['unit']}{var['entity']}，我們將分子單位現有值相減。{分配物值}-{var['value']}={int(k)}為分子單位。  "
                    分配物值 -= float(var['value'])
                   

        # If 分配物值 has changed, update it; otherwise, keep the original value
        if 分配物值 != original_value:
            input_data['分配物值'] = str(float(分配物值))  # Convert to float to preserve decimal places
            # input_data['Formula'] += f"{分配物值}"
            
        else:
            input_data['分配物值'] = str(float(original_value))

        return input_data
    
    def variable_entailment(self, input_data):
        if input_data.get('matched_clue') is not None:
            return input_data
        if input_data.get('分配物值') is not None and input_data.get('分配量') is not None:
            return input_data

        
        分配物值 = None
        分配量 = None
        
        # Find the largest s+num by comparing only the first digit after 's'
        max_sentence = max(
            (var['sentence'] for var in input_data['Variable'].values() if var['sentence'].startswith('s')),
            key=lambda x: int(x[1])
        )
        
        # Iterate through variables to find 分配物值 and 分配量
        for var_key, var in input_data['Variable'].items():
            # Skip if the sentence is the largest s+num
            if var['sentence'] == max_sentence:
                continue
            
            if (分配物值 is None and 
                var['unit'] == input_data['target_分子_unit'] and 
                var['entity'] == input_data['target_分子_entity']):
                # print( var['value'])
                分配物值 = var['value']
                input_data['Description'] += f"題意出現({var['value']}{input_data['target_分子_unit']}{var['entity']})，與問句分子所求相等，將{var['value']}視為分子單位。"
                input_data['Variable'][var_key]['unit'] = "used"
                input_data['Variable'][var_key]['value'] = 0
                input_data['Variable'][var_key]['entity'] = "used"
                input_data['Variable'][var_key]['is_original'] = True  
                input_data['Formula'] += f"{分配物值}"
                input_data['fraction_value'] = f"{分配物值}"
                break
        
        # Separate loop for 分配量
        for var_key, var in input_data['Variable'].items():
            # Skip if the sentence is the largest s+num
            if var['sentence'] == max_sentence:
                continue
            
            if (分配量 is None and 
                var['unit'] == input_data['target_分母_unit'] and 
                var['entity'] == input_data['target_分母_entity']):
                
                分配量 = var['value']
                input_data['Description'] += f"題意出現({var['value']}{input_data['target_分母_unit']}{var['entity']})，與問句分母所求相等，將{var['value']}視為分母單位。"
                input_data['Variable'][var_key]['unit'] = "used"
                input_data['Variable'][var_key]['entity'] = "used"
                break
        
        # Update the input_data
    
        input_data['分配物值'] = 分配物值
        input_data['分配量'] = 分配量
        
        return input_data
# Example usage:
# result = combined_unitmaps(self, input_data)
    
    #把單位換成一致演算法
    def process_units(self, data, converter):
        # Get the length of stype and determine target sentence
        stype_length = len(data['stype'])
        target_sentence = f's{stype_length}'

        # Find variables with the target sentence
        target_variables = [var for var, info in data['Variable'].items() if info['sentence'] == target_sentence]
        
        # Get target units
        target_units = [data['Variable'][var]['unit'] for var in target_variables]

        # Iterate through other variables and convert if necessary
        for var, info in data['Variable'].items():
            if var not in target_variables:
                current_unit = info['unit']
                current_category = converter.unit_category_map.get(current_unit)
                
                for target_unit in target_units:
                    target_category = converter.unit_category_map.get(target_unit)

                    if current_unit == target_unit:
                        continue
                    
                    if current_category == target_category and current_category in ['length', 'time', 'volume', 'weight']:
                        # Get the correct factor dictionary
                        if current_category == 'length':
                            factors = converter.length_factors
                        elif current_category == 'time':
                            factors = converter.time_factors
                        elif current_category == 'volume':
                            factors = converter.volume_factors
                        elif current_category == 'weight':
                            factors = converter.weight_factors
                        
                        # Convert the value
                        current_value = float(info['value'])
                        converted_value = current_value * factors[current_unit] / factors[target_unit]
                        
                        # Update the variable information
                        data['Variable'][var]['value'] = str(converted_value)
                        data['Variable'][var]['unit'] = target_unit
                        break

        return data
    
    def process_two_qs(self, first_number, second_number):
    # Convert both inputs to Fraction objects
        first = Fraction(first_number)
        second = Fraction(second_number)

        # print(first_number, second_number)
        
        # Calculate the product and get its integer part
        product = first * second
        int_part = int(product)
        
        # Calculate the second output
        result = (first.numerator * second.numerator - int_part * first.denominator * second.denominator) % (first.denominator * second.denominator)
        
        return (int_part, result)  
    
    #解題演算法
    def solve_unitmap(self, input_data):
        ratio = input_data['ratio']
        value = input_data['Variable'][input_data['matched_clue']]['value']
        value_fraction = Fraction(value)
       
        if self.check_two_questions(input_data):
            my_answer =self.process_two_qs(ratio,value_fraction)
            output = {
                "Question ID": input_data['QuestionID'],
                "Question Type": "Double",
                "Description": input_data['Description'],
                "target_分子_unit":input_data['target_分子_unit'],
                "Formula": "",
                "My Answer": str(my_answer),
                "Solution": input_data['Answer']
            }
            show_data={
                "Question ID": input_data['QuestionID'],
                "Description": input_data['Description'],
                "Formula": "",
                "My Answer": f"{str(my_answer)}{input_data['target_分子_unit']}"
            }
            print(show_data)
            return output
         
        else:
            if input_data["matched_clue"] is None:
                raise ValueError("matched_clue not found")
        
            ratio = input_data['ratio']
            value = input_data['Variable'][input_data['matched_clue']]['value']
        
        # Convert the fraction string to a Fraction object
            value_fraction = Fraction(value)
        
        # Multiply the ratio by the value
            my_answer = Fraction(ratio) * value_fraction
         
            input_data['Description'] += f"透過前面推論可得，當有{input_data['ratio']}{input_data['target_分母_unit']}{input_data['target_分母_entity']}時，{input_data['target_分子_entity']}對應的{input_data['target_分子_unit']}數為 {ratio}*{value_fraction} ={my_answer}。 答:{my_answer}{input_data['target_分子_unit']}"
            input_data['Formula']+= f"{ratio} * {input_data['fraction_value']} = {my_answer}"
            output = {
                "Question ID": input_data['QuestionID'],
                "Question Type": "Single",
                "Description": input_data['Description'],
                "target_分子_unit":input_data['target_分子_unit'],
                "Formula": input_data['Formula'],
                "My Answer": str(my_answer),
                "Solution": input_data['Answer']
            }
            

            show_data={
                "Question ID": input_data['QuestionID'],
                "Description": input_data['Description'],
                "Formula": input_data['Formula'],
                "My Answer":f"{str(my_answer)}{input_data['target_分子_unit']}"
            }
            print(show_data)
            
            return output
    
    #幾公分幾毫米換成公分毫米
    def process_combination_data(self, input_data, converter):
        if 'target_分子_unit' in input_data and input_data['target_分子_unit'] is not None:
            target_unit = input_data['target_分子_unit']
            if len(target_unit) == 4 and target_unit != "平方公尺" and target_unit != "平方公分":
                # Convert 'My Answer' to float
                my_answer = input_data['My Answer']
                if '/' in my_answer:
                    numerator, denominator = map(float, my_answer.split('/'))
                    my_answer_float = numerator / denominator
                else:
                    my_answer_float = float(my_answer)

                # Split the target unit
                unit1, unit2 = target_unit[:2], target_unit[2:]
                
                # Get the conversion factor
                factor = converter.length_factors[unit1] / converter.length_factors[unit2]

                # Split into whole and fractional parts
                whole_part = int(my_answer_float)
                fraction_part = my_answer_float - whole_part

                # Convert fraction part to the smaller unit
                smaller_unit_value = int(round(fraction_part * factor))

                # Create the new 'My Answer'
                new_answer = f"{whole_part}{unit1}{smaller_unit_value}{unit2}"

                # Update the input data
                input_data['My Answer'] = new_answer


        return input_data
    
    def match_numbers(self,data):
    # Extract the solution and answer from the data
        solution = data['Solution']
        my_answer = data['My Answer']
    
    # Remove Chinese characters and split by semicolon
        solution_numbers = [int(n) for n in ''.join(c if c.isdigit() or c == ';' else '' for c in solution).split(';')]
    
    # Parse My Answer string
        match = re.match(r'\((\d+),\s*Fraction\((\d+),\s*(\d+)\)\)', my_answer)
        if not match:
            return False
    
        answer_number = int(match.group(1))
        fraction_numerator = int(match.group(2))
        fraction_denominator = int(match.group(3))
    
    # Check if the first number from Solution equals the first number in My Answer
    # AND the second number from Solution equals the numerator of the Fraction in My Answer
        return solution_numbers[0] == answer_number and solution_numbers[1] == fraction_numerator

    #評估
    def eval_data(self, input_data):
        # Extract 'My Answer' and 'Solution' from input_data
        if input_data.get('My Answer', '') == input_data.get('Solution', ''):
            return True
        
        if input_data['Question Type'] == "Double":
            solution = input_data['Solution']
            solution = self.extract_two_answers(solution)
            my_answer = self.parse_my_answer(input_data['My Answer'])
            return solution == my_answer


        my_answer = input_data.get('My Answer', '').strip()
        solution = input_data.get('Solution', '').strip()

        # Remove Chinese characters from the solution
        solution_cleaned = re.sub(r'[\u4e00-\u9fff]+', '', solution)
        
        # Remove any leading/trailing whitespace
        solution_cleaned = solution_cleaned.strip()
        
        # Compare the cleaned solution with my_answer
        if solution_cleaned == my_answer:
            return True
        else:
            # Evaluate the mathematical expression in 'My Answer'
            try:
                my_answer_value = eval(my_answer)
            except Exception as e:
                return False
            
            # Convert the cleaned solution to a float
            try:
                solution_value = float(solution_cleaned)
            except ValueError:
                return False
            
            # Compare the evaluated answer with the solution value
            return my_answer_value == solution_value

    

    def solve(self, extracted_data):
        converter = UnitConverter()
 
        phase1 = self.process_data(extracted_data)
        phase2 = self.convert_mixed_fractions(phase1)
        

        phase3 = self.find_asked_unitmap(phase2)
        phase4 = self.process_units(phase3,converter)
        phase5 = self.process_unitmap(phase4)
        phase5 = self.combined_unitmaps(phase5)

        # print(phase5)

    
        phase7 = self.process_portion_scan(phase5)
  
        #變數與unitmap相乘(一包米5元，爸爸買了10包米)
        # print(phase7)
        phase7 = self.variance_map_unitmap(phase7)
        #從文字找出對應的變數
        # print(phase7)
        phase7 = self.variable_entailment(phase7)
        phase7 = self.track_variable_value(phase7)
        # print(phase7)

        
        phase7 = self.process_left(phase7)
        # print(phase7)
        

        
        phase7 = self.mixed_unitmap(phase7)
        # print(phase7)
        phase7 = self.solve_unitmap(phase7)
        phase8 = self.process_combination_data(phase7,converter)
        phase9= self.eval_data(phase8)
        # print(phase8)
        
        
        return phase9
    

class UnitConverter:
    def __init__(self):
        self.length_factors = {'公分': 0.01, '公尺': 1, '毫米': 0.001, '公里': 1000, "公分毫米": 0.01, "公里公尺": 1000, "公尺公分": 1}
        self.time_factors = {'秒': 1, '分': 60, '分鐘': 60, '時': 3600, '小時': 3600, "分秒": 60, "分鐘秒": 60, "小時分鐘": 3600, "天": 86400, "星期": 604800}
        self.volume_factors = {'毫升': 0.001, '公升': 1, 'cc': 0.001}
        self.weight_factors = {'公克': 1, '公斤': 1000, '公噸': 1000000, 'g': 1, '毫克': 0.001}
        self.unit_factors = {'隻': 1, "雙": 2, '朵': 1, '束': 1}

        self.unit_category_map = {}
        for category, factors in {'unit': self.unit_factors,
                                  'length': self.length_factors, 'time': self.time_factors, 'volume': self.volume_factors, 'weight': self.weight_factors}.items():
            for unit in factors:
                self.unit_category_map[unit] = category
