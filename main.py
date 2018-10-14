from os import listdir
from os.path import isfile, join
from collections import OrderedDict
import sys
import io
import struct
import math
import re
import xml.etree.ElementTree as ElTree
import terminal


class Index:
    def __init__(self, path):

        self.docs_indexed = 0
        # In-memory representation of the posting list
        self.__binary_pl = io.BytesIO(b"")
        self.voc = {}
        self.count = {}
        self.path = path

    @staticmethod
    def term_frequency(count_doc_occurrences):
        # see slide 8
        if count_doc_occurrences == 0:
            return 0

        return 1 + math.log10(count_doc_occurrences)

    def read_pl_for_word(self, pl_len, pl_offset, pl_row_len=8):
        pl = OrderedDict()
        with open(self.path, 'rb') as pl_file:
            pl_file.seek(pl_offset)
            while pl_file.tell() < pl_offset + pl_len:
                byte_row = pl_file.read(pl_row_len)
                pl_struct = struct.unpack('!If', byte_row)
                pl.update({pl_struct[0]: pl_struct[1]})
        return pl

    def read_nth_entry_from_pl(self, n, pl_offset, pl_row_len=8):
        with open(self.path, 'rb') as pl_file:
            pl_file.seek(pl_offset + (n * pl_row_len))
            byte_row = pl_file.read(pl_row_len)
            item = struct.unpack('!If', byte_row)
        return item

    def write_pl_row(self, document, score):
        binary_pack = struct.pack('!If', document, score)
        self.__binary_pl.write(binary_pack)
        # write PL in memory to disk if it exceeds one MB in size
        if self.__binary_pl.tell() > 1024000:
            self.save_pl_to_disk()

        return len(binary_pack)

    def save_pl_to_disk(self):
        # Open file and read buffer into it
        self.__binary_pl.seek(0)
        with open(self.path, 'wb') as out:
            out.write(self.__binary_pl.read())
        self.__binary_pl.close()
        self.__binary_pl = io.BytesIO(b"")

    def finalize_pl(self):
        self.save_pl_to_disk()

    def inverse_document_freq(self, num_where_appeared):
        # see slide 10
        return math.log10(self.docs_indexed / (1 + num_where_appeared))

    @staticmethod
    def get_element_inner_text(element, xpath):
        if element is None:
            return ""
        found = element.find(xpath)
        if found is None:
            return ""
        return "".join(found.itertext())

    def index_folder(self, folder_name):
        # Open files from specified folder
        files = [f for f in listdir(folder_name) if isfile(join(folder_name, f))]
        # Increase number of indexed documents by the amount of docs found
        self.docs_indexed = self.docs_indexed + len(files)
        print("Adding {} files to index".format(len(files)))

        terminal.print_progress(0,
                                len(files),
                                prefix='Step 1 of 2: ',
                                suffix='Complete',
                                bar_length=80)

        files_indexed = 0

        # Dictionary of term frequencies per word per doc
        tf_per_doc = {}
        for filename in files:
            with open(folder_name + filename, "r") as file:
                text = ""
                for line in file:
                    text += line
                text = "<DOCCOLLECTION>" + text + "</DOCCOLLECTION>"

                docs = ElTree.fromstring(text)

                articles_indexed = 0
                for article in docs:
                    doc_id = int(article.find('./DOCID').text.strip()) + (files_indexed * (10 ** 6))
                    terminal.print_progress(files_indexed + (articles_indexed / len(docs)),
                                            len(files),
                                            prefix='Step 1 of 2: ',
                                            suffix='Complete, (doc {} from file {})'.format(doc_id, filename),
                                            bar_length=80)

                    # print("Adding document {} from file {} to index".format(doc_id, filename))
                    important_stuff = Index.get_element_inner_text(article, './HEADLINE') + '\n' \
                        + Index.get_element_inner_text(article, './BYLINE') + '\n' \
                        + Index.get_element_inner_text(article, './TEXT') + '\n' \
                        + Index.get_element_inner_text(article, './SUBJECT') + '\n' \
                        + Index.get_element_inner_text(article, './GRAPHIC') + '\n'

                    # TODO save (reference?) to original document
                    # Lowercase as early as possible, reduces amount of calls
                    important_stuff = important_stuff.lower()
                    # Remove punctuation from words
                    words = re.split('[. ()\[\]\-",:;\n!?]', important_stuff)
                    for w in words:
                        # Set up dictionary
                        if w not in tf_per_doc:
                            tf_per_doc[w] = {}
                        if doc_id not in tf_per_doc[w]:
                            tf_per_doc[w][doc_id] = 0
                        tf_per_doc[w][doc_id] += 1
                    # Calculate tf for each entry
                    for w in words:
                        tf_per_doc[w][doc_id] = Index.term_frequency(tf_per_doc[w][doc_id])
                    articles_indexed += 1

                files_indexed += 1
        # Temporary dictionary with the idfs to prepare for the posting list creation
        inverted_document_freqs = {}

        terminal.print_progress(0,
                                len(tf_per_doc),
                                prefix='Step 2 of 2: ',
                                suffix='Complete',
                                bar_length=80)

        words_treated = 0
        pl_offset = 0
        # Iterate words from tf dictionary
        for word, documents in tf_per_doc.items():
            # Calculate idf values
            inverted_document_freqs[word] = self.inverse_document_freq(len(documents))
            # Filter for stop words
            if inverted_document_freqs[word] < 0:
                continue

            docs_treated = 0
            pl_len = 0
            # Calculate score for each element of the posting list
            for document, term_frequency in documents.items():
                terminal.print_progress(words_treated + (docs_treated / len(documents)),
                                        len(tf_per_doc),
                                        prefix='Step 2 of 2: ',
                                        suffix='Complete (Writing PL for {})'.format(word),
                                        bar_length=80)
                pl_len += self.write_pl_row(document, term_frequency * inverted_document_freqs[word])
                docs_treated += 1
            self.voc[word] = (pl_len, pl_offset)
            pl_offset += pl_len
            words_treated += 1

        self.finalize_pl()
        print("\nSuccess")

    def print_index_stats(self):
        print("Words in index")
        print(len(self.voc))
        print('====')
        print(self.docs_indexed)
        # TODO MOOOORE


class Searcher:
    def __init__(self, index):
        self.index = index

    def search(self, a_word):
        if a_word in self.index.voc:
            pl = self.index.read_pl_for_word(*(self.index.voc[a_word]))
            for document, score in pl.items():
                print('Document: ', document, '---', 'Frequency: ', score)
        else:
            print("Word not found")


def main():
    print("\nWelcome to the research engine")
    print("==============================")

    if len(sys.argv) < 2:
        print("Please specify the name for the posting list file in an argument")
        print("Usage example: {} ./data/pl-file".format(sys.argv[0]))
        exit(-1)

    path = sys.argv[1]
    m = re.search('((?<=^["\']).*(?=["\']$))', path)
    if m is not None:
        path = m.group(0)

    # Get a instance of our index and search
    index = Index(path)
    searcher = Searcher(index)
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

        if menu_item is None:
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
            index.index_folder(folder)
        elif menu_item == 2:
            a_word = input('Please enter your word: ')
            searcher.search(a_word)
            pass
        elif menu_item == 3:
            index.print_index_stats()
        elif menu_item == 4:
            exit(0)
        else:
            print("Unknown menu item")


if __name__ == "__main__":
    main()
