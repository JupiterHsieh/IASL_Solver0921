import json
from quantity_extraction import QuantityExtraction

class GenerateTrainingSet:
    def __init__(self, base_url):
        self.base_url = base_url
        self.qe = QuantityExtraction(self.base_url)

    def merge_data(self, first_data, second_data):
        # Merging the data
        first_data['qid'] = second_data['qid']
        first_data['sentence'] = second_data['question']
        first_data['answer'] = second_data['answer']
        first_data['stype'] = [sentence['stype'] for sentence in second_data['sentences']]

        # Check if there are followers and append their stype
        if 'followers' in second_data and second_data['followers']:
            first_data['stype'].extend([follower['stype'] for follower in second_data['followers']])

        return first_data

    def generate_training_set(self, data):
        parsing_sentence = data['question']
        result = self.qe.get_parsing_data(parsing_sentence)
        training_data = self.merge_data(result, data)
        return training_data