from .iasl_solver import IASL_Solver

class Refund_Solver(IASL_Solver):
    def process_data(self, extracted_data):
        output = super().process_data(extracted_data)
        output['已買物品'] = None
        output["花的錢"] = None
        with open('knowledge\payment_verbs.txt', 'r', encoding='utf-8') as file:
            self.payment_verbs = [line.strip() for line in file]

        return output
    

    # 如果動詞是付錢的動詞 sentence type 是量變就把他當成花的錢
    def find_money_paid(self, input_data):
        # Define the payment verbs
        # Find the indexes of '量變' in stype
        indexes_of_variance = [i for i, stype in enumerate(input_data['stype']) if stype == '量變']

        # Find the Variables that have sentence 's' + (index + 1) where index is in indexes_of_variance
        target_variables = []
        for index in indexes_of_variance:
            sentence_key = 's' + str(index + 1)
            for var_key, var_value in input_data['Variable'].items():
                if var_value['sentence'] == sentence_key:
                    target_variables.append((var_key, index))

        for var_key, index in target_variables:
            if input_data['Variable'][var_key]['verb'] in self.payment_verbs:
                input_data['Variable'][var_key]['clue'] = '已付'
      
                # Update the stype for the corresponding index
                input_data['stype'][index] = '量變'
                input_data['花的錢'] = True
                input_data['Description'] += f"此題為問找回，我們先找付的錢。可在第{index+1}句裡的'{input_data['Variable'][var_key]['verb']}'得知，付了{input_data['Variable'][var_key]['value']}塊錢。{input_data['Variable'][var_key]['value']}為已付。"
                input_data['Formula'] += str(input_data['Variable'][var_key]['value'])
        
        return input_data


    def solve_refund(self, input_data):
        variables = input_data['Variable']
        
        paid_money = None
        for key, var in variables.items():
            if var['clue'] == '已付':
                paid_money = int(var['value'])  # Convert the value to an integer
                break
        
        # Ensure pay_var is found
        if paid_money is None:
            raise ValueError("No variable with clue '已付' found.")
        
        # Step 2: Find the variables with the clue '已買價格'
        buy_price_vars = []
        for key, var in variables.items():
            if var['clue'] == '已買價格':
                buy_price_vars.append(int(var['value']))  # Convert the value to an integer
        
        # Ensure there are variables with the clue '已買價格'
        if not buy_price_vars:
            raise ValueError("No variables with clue '已買價格' found.")
        
        # Step 3: Do the math: pay_var minus all '已買價格' values
        total_bought_price = sum(buy_price_vars)
        my_answer = paid_money - total_bought_price
        
        input_data['Description'] += f"計算應買總價格={total_bought_price}。將已付減去應付總價極為所求。{paid_money} - {total_bought_price} = {my_answer}。"
        
        output = {
            "Question ID": input_data['QuestionID'],
            "Question Type": "Single",
            "Description": input_data['Description'],
            "Formula": "",
            "My Answer": my_answer,
            "Solution": input_data['Answer']
        }
        
        return output


    def solve(self, extracted_data):

        phase1 = self.process_data(extracted_data)
        
        # print(phase1)
        phase2 = self.find_money_paid(phase1)
        # print(phase2)
        phase3 = self.tag_item_price(phase2)
        # print(phase3)
        phase4 = self.calculate_bought_item_price(phase3)
        # print(phase4)
        phase5 = self.solve_refund(phase4)
        print(phase5)
        phase6 = self.eval_data(phase5)
        # print(phase6)
        return phase6