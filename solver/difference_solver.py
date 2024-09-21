from .iasl_solver import IASL_Solver

class Difference_Solver(IASL_Solver):
    def process_data(self, extracted_data):
        output = super().process_data(extracted_data)
        output["第一比較物"] = None
        output["第二比較物"] = None
        output["共有"] = None
        return output
    








    def solve(self, extracted_data):
        phase1 = self.process_data(extracted_data) 
        print(phase1)
