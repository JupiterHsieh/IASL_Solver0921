from solver.iasl_solver import IASL_Solver
from utils.unitconverter import UnitConverter
import re


class Portion_Solver(IASL_Solver):
    def process_data(self, extracted_data):
        output = super().process_data(extracted_data)
        output["可分配物"] = None
        output["分配量"] = None
        return output

    def start_variable_clue(self, input_data):
        for i, stype_value in enumerate(input_data['stype']):
                if stype_value == '有':
                    target_sentence = 's' + str(i + 1)
                    for key, variable in input_data['Variable'].items():
                        if variable['sentence'] == target_sentence:
                            # Add the "可分配物" clue to the variable
                            variable['clue'] = "可分配物"
                            entity = variable['entity']
                            value = variable['value']
                            unit = variable['unit']

                            input_data["可分配物"] = True
                            input_data['Description'] += f" Initial Scan: 第{target_sentence[-1]}句的意思是原有，因此將({entity}{value}{unit})視為目前的可分配物。 "
                            input_data['Formula'] += str(value)
                            break
                    break
        return input_data
    
    def find_target(self, data):
    # 1. Find the variables with 'value' == "?"
        target_variables = []
        for key, variable in data['Variable'].items():
            if variable['value'] == '?':
                target_variables.append(variable)
                if len(target_variables) == 2:
                    break
        
        # 2. Add new columns to the whole data
        if target_variables:
            data["target_unit"] = target_variables[0]['unit']
            data["target_entity"] = target_variables[0]['entity']
            
            if len(target_variables) == 2:
                data["target_unit2"] = target_variables[1]['unit']
                data["target_entity2"] = target_variables[1]['entity']
        
        # 3. Return the whole data
        return data

    def determine_larger_smaller(self, key1, key2, variables, target_unit):
        value1 = float(variables[key1]['value'])
        value2 = float(variables[key2]['value'])
        unit1 = variables[key1]['unit']
        unit2 = variables[key2]['unit']

        if unit1 == target_unit:
            return key2, value2, key1, value1
        elif unit2 == target_unit:
            return key1, value1, key2, value2
        else:
            # If none match, use the original logic
            if value1 == 1.0:
                return key2, value2, key1, value1
            elif value2 == 1.0:
                return key1, value1, key2, value2
            else:
                return (key1, value1, key2, value2) if value1 > value2 else (key2, value2, key1, value1)

    def unitmap_to_formula(self, input_data, sentence):
        variables = input_data['Variable']
        used_variables = set(variables.keys())
        unused_variables = [v for v in self.variable_list if v not in used_variables]
        target_unit = input_data.get('target_unit', '')

        occurrence_counter = 1
        matching_vars = [k for k, v in variables.items() if v['sentence'] == sentence]

        if len(matching_vars) < 2:
            print(f"Not enough variables found for sentence {sentence}. Expected 2, found {len(matching_vars)}.")
            return input_data

        x_key1, x_key2 = matching_vars[:2]
        if x_key1 in variables and x_key2 in variables:
            larger_key, larger_value, smaller_key, smaller_value = self.determine_larger_smaller(x_key1, x_key2, variables, target_unit)

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
    

    def variance_entailment(self, input_data):
        if input_data.get('可分配物') is not None:
            return input_data

        if input_data.get('可分配物') is None:
            # Find the first occurrence of '量變' in 'stype'
            for i in range(len(input_data['stype'])):
                if input_data['stype'][i] == "量變":
                    target_index = i
                    target_sentence = 's' + str(i + 1)
                    break
            else:
                return input_data

            for key, variable in input_data['Variable'].items():
                if variable['sentence'] == target_sentence:
                    # Add the "可分配物" clue to the variable
                    variable['clue'] = "可分配物"
                    entity = variable['entity']
                    value = variable['value']
                    unit = variable['unit']
                    input_data["可分配物"] = True
                    input_data['Description'] += f" Initial Scan: 第{target_sentence[-1]}句的意思是原有，因此將({entity}{value}{unit})視為目前的可分配物。 "
                    input_data['Formula'] += str(value)

                    # Change the target 'stype' from '量變' to '有'
                    input_data['stype'][target_index] = "有"
                    break

        return input_data

    def process_portion_scan(self, input_data):
        for i in range(0, len(input_data['stype'])):
            if input_data['stype'][i] == "平分":
                # Identify the sentence corresponding to the next index after the current "平分" index
                target_sentence = 's' + str(i + 1)
                # Search for the variable that uses this sentence
                for variable, details in input_data['Variable'].items():
                    if details['sentence'] == target_sentence:
                        # If found, add "單位量" to the clue of this variable
                        input_data['Variable'][variable]['clue'] = '單位量'
                        v = input_data['Variable'][variable]['value']
                        e = input_data['Variable'][variable]['entity']
                        u  = input_data['Variable'][variable]['unit']

                        input_data['Description'] += f"Portion Scan : 第{str(i + 1)}句為平分，因此{v}{u}{e}為此題的分配量。 "
                
        return input_data
    
    def unitmap_entailment(self,input_data):
        # Check if '可分配物' is True or False
        if not input_data['可分配物']:
            # Iterate over variables to find specific conditions and modify accordingly
            for key, value in input_data['Variable'].items():
                if value['sentence'] == 's1' and value['value'] != 1:
                    input_data['Variable'][key]['clue'] = "可分配物"
                    input_data['Description'] += f"將第一句的{input_data['Variable'][key]['entity']}視為可分配物。 "
                    # print(input_data['Variable'][key]['value'])
                    input_data['Formula'] +=  str(input_data['Variable'][key]['value'])
                    input_data["可分配物"] = True
                if value['sentence'] == 's1-1':
                    input_data['Variable'][key]['clue'] = None


        return input_data
    
    def track_variable_clue_unitmap(self,input_data):
        # Step 1: Count 'Variable' with clue '單位量'
        unitmap_vars = [key for key, var in input_data['Variable'].items() if var.get('clue') == '單位量']

        if len(unitmap_vars) < 2:
            return input_data
        # Step 4: Find the Variable with clue '可分配物'
        distributable_var_key = next(key for key, var in input_data['Variable'].items() if var.get('clue') == '可分配物')
        distributable_var = input_data['Variable'][distributable_var_key]
        
        # Step 5: Get the first '單位量' Variable
        first_unitmap_var_key = unitmap_vars[0]
        first_unitmap_var = input_data['Variable'][first_unitmap_var_key]
        
        # Step 6: Calculate new_var_value
        new_var_value = float(distributable_var['value']) / float(first_unitmap_var['value'])
        
        # Step 7: Create new variable X80
        new_var_key = 'X80'
        input_data['Variable'][new_var_key] = {
            'value': new_var_value,
            'unit': distributable_var['unit'],
            'entity': distributable_var['entity'],
            'meaning': None,
            'sentence': distributable_var['sentence'],
            'clue': '可分配物'
        }
        
        input_data['Variable'][distributable_var_key]['clue'] = '原分配物'
        input_data['Variable'][first_unitmap_var_key]['clue'] = '中間使用單位量'
        input_data['Formula'] += f" / { float(first_unitmap_var['value'])}"
        input_data['Formula'] = self.add_parentheses( input_data['Formula']) 
        
        return input_data
    
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
    
    def process_unit(self,data, unit_converter):
        variables = data['Variable']
        units = {var: variables[var]['unit'] for var in variables}
        
        for var1 in variables:
            for var2 in variables:
                if var1 != var2:
                    unit1 = units[var1]
                    unit2 = units[var2]
                    
                    if unit1 in unit_converter.unit_category_map and unit2 in unit_converter.unit_category_map:
                        category1 = unit_converter.unit_category_map[unit1]
                        category2 = unit_converter.unit_category_map[unit2]
                        
                        if category1 == category2:
                            factors = getattr(unit_converter, f"{category1}_factors")
                            if factors[unit1] > factors[unit2]:
                                value = float(variables[var1]['value']) * factors[unit1] / factors[unit2]
                           
                                variables[var1]['value'] = str(value)
                                variables[var1]['unit'] = unit2
        
        return data
    
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

    def calculate_values(self,v1, v2):
        if v1 % v2 == 0:
            s1 = v1 // v2
            s2 = v1 % v2
        else:
            s1 = v1 // v2
            s2 = v1 - (v2 * s1)
            s2 = round(s2, 2)
        
        return s1, s2
    
    def solve_portion(self,data):
        # Initialize variables
        v1 = None
        v1_unit = None
        v2 = None
        v2_unit = None
        description = data['Description']
        formula = data['Formula']
        
        # Find variables by clue
        for key, value in data['Variable'].items():
            if value['clue'] == '可分配物':
                v1 = float(value['value'])
                v1_unit = value['unit']
                v1_entity = value['entity']
            elif value['clue'] == '單位量':
                v2 = float(value['value'])
                v2_unit = value['unit']
        # Check if both variables are found
        if v1 is None and v2 is None:
            return "可分配物 and 單位量 not found"
        elif v1 is None:
            return "可分配物 not found "
        elif v2 is None:
            return "單位量 not found "
            
        if self.check_two_questions(data):
            s1,s2 =self.calculate_values(v1,v2)
            description += f"Final Scan: 分配量=可分配物 / 分配量(單位量)， 因此，本題解法為{v1} / {v2} = {s1}，剩下{s2}"
            solution = data['Answer']
            formula += f" / {v2} = {s1}...{s2}"
            output = {
                "Question ID": data['QuestionID'],
                "Question Type":"Double",
                "Description": description,
                "Formula":formula,
                "My Answer": f"{s1,s2}",
                "Solution": solution
            }
            output_data ={
                "Formula":formula,
                "My Answer":  f"{s1}{data['target_unit']};{s2}{data['target_unit2']}"
            }
            print(output_data)
           
            # if output['Formula'] :
            #     print(output['Formula'])
            # else:
            #     print("Not yet ")
            # print(output['Formula'])
        else:
            my_answer = v1 / v2
            my_answer = round(my_answer,2)
            formula += f" / {v2} = {my_answer}"
            
            description += f"Final Scan: 分配量=可分配物 / 分配量(單位量)， 因此，本題解法為{v1} {v1_unit}{v1_entity}  / ({v2}{v2_unit}) = {my_answer:.1f}"
            solution = data['Answer']
            # Output dictionary
            output = {
                "Question ID": data['QuestionID'],
                "Question Type":"Single",
                "Description": description,
                "Formula":formula,
                "My Answer": f"{my_answer}",
                "Solution": solution
            }
            output_data ={
                "Formula":formula,
                "My Answer": f"{my_answer}{data['target_unit']}",
            }
            print(output_data)
            # if output['Formula'] :
            #     print(output['Formula'])
            # else:
            #     print("Not yet ")
            # print(output['Formula'])


        return output

    def eval_data(self, input_data):
        # Extract 'My Answer' and 'Solution' from input_data
        if input_data.get('My Answer', '') == input_data.get('Solution', ''):
            return True
        
        if input_data['Question Type'] == "Single":
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
            
        else:
            solution = input_data['Solution']
            solution = self.extract_two_answers(solution)
            my_answer = self.parse_my_answer(input_data['My Answer'])
            return solution == my_answer
    
    
    def solve(self, extracted_data):

        #讀資料+轉換單位
        converter = UnitConverter()
        phase1 = self.process_data(extracted_data)
        phase2 = self.process_unit(phase1,converter)
        phase2 = self.find_target(phase2)
    
        #找分配物
        phase3 = self.start_variable_clue(phase2)
        # print(phase3)
        phase4 = self.variance_entailment(phase3)
        
     
        phase5 = self.process_unitmap(phase4)
       
        phase6 = self.unitmap_entailment(phase5)

        #演算法
        phase7 = self.process_portion_scan(phase6)
        phase8 = self.adjust_object_variance(phase7, clue='可分配物')
        phase9 = self.adjust_object_left(phase8, clue='可分配物')
        phase10 = self.track_variable_clue_unitmap(phase9)

        #解題
        phase11= self.solve_portion(phase10)
        # print(phase11)
        return self.eval_data(phase11)
        

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
    
