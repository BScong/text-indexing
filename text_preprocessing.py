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

class StopwordPreparation(ILinePreparation):
    def __init__(self):
        self.stoppers = ["a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
                         "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
                         "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
                         "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
                         "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
                         "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
                         "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
                         "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
                         "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
                         "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
                         "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
                         "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
                         "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
                         "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
                         "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
                         "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"]

    def prepare_line(self, line):
        query_words = line.split()

        result_words = [word for word in query_words if word.lower() not in self.stoppers]
        return ' '.join(result_words)

class StemmingPreparation(IWordPreparation):
    def prepare_word(self, word):
        return stem(word)
        # return word
        # faster

def get_instances_of_all_word_preparators(stemming=False):
    return [StemmingPreparation()] if stemming else []

def get_instances_of_all_line_preparators(stopwords=False):
    filters = [LowercasePreparation(), DeleteCharacterPreparation()]
    if stopwords:
        filters.append(StopwordPreparation())
    return filters