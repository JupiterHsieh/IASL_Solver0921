import requests

class QuantityExtraction:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_parsing_data(self, sentence):
        payload = {"sentence": sentence}
        
        # Perform the parsing request
        ss_result = requests.post(f'{self.base_url}/IASL_Parsing', json=payload)
        ss_result_json = ss_result.json()
        
        # Perform the quantity extraction request
        qe_result = requests.post(f'{self.base_url}/Quantity_Extraction', json=ss_result_json)
        qe_result_json = qe_result.json()
        
        return qe_result_json
