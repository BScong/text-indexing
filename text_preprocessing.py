import re

# pip install stemming
from stemming.porter2 import stem


class ILinePreparation:
    def prepare_line(self, line):
        raise NotImplementedError("All inheriting line preparators should implement this method")


class IWordPreparation:
    def prepare_word(self, text):
        raise NotImplementedError("All inheriting word preparators should implement this method")


class LowercasePreparation(ILinePreparation):
    def prepare_line(self, line):
        return line.lower()


class DeleteCharacterPreparation(ILinePreparation):
    def __init__(self):
        self.filter_characters = '[. ()\[\]\-",:;\n!?]|[0-9]+'

    def prepare_line(self, line):
        return re.sub(self.filter_characters, ' ', line)


class StemmingPreparation(IWordPreparation):
    def prepare_word(self, word):
        # return stem(word)
        return word
        # faster

def get_instances_of_all_word_preparators():
    return [StemmingPreparation()]

def get_instances_of_all_line_preparators():
    return [LowercasePreparation(), DeleteCharacterPreparation()]