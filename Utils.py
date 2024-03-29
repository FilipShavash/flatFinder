import csv
import json


class Utils:
    @staticmethod
    def save_json_file(filename, content):
        with open(filename, 'w', encoding='utf8') as outfile:
            json.dump(content, outfile, sort_keys=True, indent=4, ensure_ascii=False)  # sort_keys = True, indent = 4

    @staticmethod
    def read_json_file(filename):
        file = open(filename, 'r', encoding='utf8')
        return json.load(file)

    @staticmethod
    def save_file(filename, content):
        with open(filename, 'w', encoding='utf8') as outfile:
            outfile.write(content)

    @staticmethod
    def read_file(filename):
        file = open(filename, 'r', encoding='utf8')
        return file.read()

    @staticmethod
    def save_csv_file(filename, data):
        with open(filename, mode='w', encoding='utf8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(data)

    @staticmethod
    def deleteDuplicates(items):
        i = 1
        while i < len(items):
            if items[i]['id'] == items[i - 1]['id']:
                items.pop(i)
                i -= 1
            i += 1
