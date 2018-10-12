from os import listdir
import math
from os.path import isfile, join
import re

global words
global docs_indexed

class Index:
    def __init__(self):

        # Dictionary of term frequencies per word per doc
        self.tf_per_doc = {}
        self.docs_indexed = 0
        # In-memory representation of the posting list
        self.posting_list = {}

    def term_frequency(self, count_doc_occurrences):
        # see slide 8
        if count_doc_occurrences == 0:
            return 0

        return 1 + math.log10(count_doc_occurrences)

    def inverse_document_freq(self, num_where_appeared):
        # see slide 10
        return math.log10(self.docs_indexed / (1 + num_where_appeared))

    def indexFolder(self, folder_name):
        # Open files from specified folder
        files = [f for f in listdir(folder_name) if isfile(join(folder_name, f))]
        # Increase number of indexed documents by the amount of docs found
        self.docs_indexed = self.docs_indexed + len(files)
        print("Adding {} documents to index".format(len(files)))
        # TODO draw progress bar

        for f in files:
            text = open(folder_name + f, "r")
            for line in text:
                # TODO save (reference?) to original document
                # Remove tags
                line = re.sub('<.+?>', ' ', line)
                # Lowercase as early as possible, reduces amount of calls
                line = line.lower()
                # Remove punctuation from words
                words = re.split('[\. ()\[\]",:-;]', line)
                for w in words:
                    # Set up dictionary
                    if w not in self.tf_per_doc:
                        self.tf_per_doc[w] = {}
                    if f not in self.tf_per_doc[w]:
                        self.tf_per_doc[w][f] = 0
                    self.tf_per_doc[w][f] += 1
                # Calculate tf for each entry
                for w in words:
                    self.tf_per_doc[w][f] = self.term_frequency(self.tf_per_doc[w][f])

        # Temporary dictionary with the idfs to prepare for the posting list creation
        inverted_document_freqs = {}

        # Fill it up
        for word, documents in self.tf_per_doc.items():
            inverted_document_freqs[word] = self.inverse_document_freq(len(documents))

        # Discard words with idf < 0 (empty, newline or stop word)
        inverted_document_freqs = {k: v for k, v in inverted_document_freqs.items() if v >= 0}
        self.tf_per_doc = {k: v for k, v in self.tf_per_doc.items() if k in inverted_document_freqs}

        # Iterate words from tf dictionary
        for word, documents in self.tf_per_doc.items():
            # Prepare posting list for new words
            if word not in self.posting_list:
                self.posting_list[word] = {}

            # Calculate score for each element of the posting list
            for document, term_frequency in documents.items():
                self.posting_list[word][document] = term_frequency * inverted_document_freqs[word]

        # TODO save pl to disk and build VOC
        print("Success")

    def printIndexStats(self):
        print("Words in index")
        print(self.posting_list)
        print('====')
        print(self.docs_indexed)
        # TODO MOOOORE

def main():
    print("\nWelcome to the research engine")
    print("==============================")

    # Get a instance of our index
    index = Index()
    # Prepare the RegEx to find numbers in our user input
    int_find = re.compile('\d+')

    # Return to the menu after tasks were accomplished
    while True:
        print("\nWhat would you like to do?")
        print("1) Add a folder of documents to the index")
        print("2) Do a search query")
        print("3) Show stats about the index")
        print("4) Exit")
        print("\n Please enter the number of a menu item")

        user_choice = input('> ')
        print("")
        # Search for digits
        menu_item = int_find.search(user_choice)

        if menu_item == None:
            print("No number found")
            continue

        # We know it's only digits, so no exception handling here
        menu_item = int(menu_item.string)

        if menu_item == 1:
            # Get a folder
            default = './data/subset/'
            print("Please enter the folder's path")
            folder = input('({}) > '.format(default)).strip()
            if folder == "":
                folder = default
            index.indexFolder(folder)
        elif menu_item == 2:
            # TODO
            pass
        elif menu_item == 3:
            index.printIndexStats()
        elif menu_item == 4:
            exit(0)
        else:
            print("Unknown menu item")

if __name__ == "__main__":
    main()
