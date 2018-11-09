from os import listdir
from os.path import isfile, join
from collections import OrderedDict
import sys
import io
import os
import struct
import math
import re
import xml.etree.ElementTree as ElTree
import terminal
import argparse

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


class Index:
    def __init__(self, path, line_preparation, word_preparation):

        self.docs_indexed = 0
        # In-memory representation of the posting list
        self.__binary_pl = io.BytesIO(b"")
        self.voc = {}
        self.count = {}
        self.path = path
        self.line_filters = line_preparation
        self.word_filters = word_preparation
        self.documents_content = {}

    @staticmethod
    def term_frequency(count_doc_occurrences, max_freq):
        # see slide 8
        if count_doc_occurrences == 0:
            return 0

        return (0.5+ 0.5*count_doc_occurrences/max_freq)

    @staticmethod
    def read_pl_for_word(pl_len, pl_offset, path, pl_row_len=8):
        pl = OrderedDict()
        with open(path, 'rb') as pl_file:
            pl_file.seek(pl_offset)
            while pl_file.tell() < pl_offset + pl_len:
                byte_row = pl_file.read(pl_row_len)
                pl_struct = struct.unpack('!If', byte_row)
                pl.update({pl_struct[0]: pl_struct[1]})
        return pl

    @staticmethod
    def read_nth_entry_from_pl(n, pl_offset, path, pl_row_len=8):
        with open(path, 'rb') as pl_file:
            pl_file.seek(pl_offset + (n * pl_row_len))
            byte_row = pl_file.read(pl_row_len)
            item = struct.unpack('!If', byte_row)
        return item

    def write_pl_row(self, document, score, path):
        binary_pack = struct.pack('!If', document, score)
        self.__binary_pl.write(binary_pack)
        # write PL in memory to disk if it exceeds one MB in size
        if self.__binary_pl.tell() > 1024000:
            self.save_pl_to_disk(path)

        return len(binary_pack)

    def save_pl_to_disk(self, path):
        # Open file and read buffer into it
        self.__binary_pl.seek(0)
        with open(path, 'ab') as out:
            out.write(self.__binary_pl.read())
        self.__binary_pl.close()
        self.__binary_pl = io.BytesIO(b"")

    def finalize_pl(self, path):
        self.save_pl_to_disk(path)

    def finalize_merge_pl(self, temp, path):
        self.save_pl_to_disk(temp)
        if os.path.exists(path):
            os.remove(path)
        os.rename(temp, path)

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

    def index_folder(self, folder_name, batch_size):
        # Open files from specified folder
        try:
            # check if folder_name is folder
            if folder_name[-1] != '/':
                folder_name = folder_name + '/'

            files = [folder_name + f for f in listdir(folder_name) if isfile(join(folder_name, f)) and 'la' in f]

            for i in range(0, len(files), batch_size):

                tfs = self.process_files(files[i:min(i + batch_size, len(files))])

                self.merge_save(tfs)

                """terminal.print_progress(min(i + batch_size, len(files)),
                                        len(files),
                                        prefix='Adding files: ',
                                        suffix='Complete',
                                        bar_length=80)"""

        except Exception as e:
            # print("Error: " + str(e))
            raise e

    def merge_save(self, tf_per_doc):
        temp_path = './pl_temp'
        pl_offset = 0
        for w in self.voc:
            pl = Index.read_pl_for_word(*(self.voc[w]), self.path)

            if w in tf_per_doc:
                for old_document in pl:
                    pl[old_document] = pl[old_document] / self.count[w][1] if self.count[w][1] != 0 else pl[old_document]
                for new_document, term_frequency in tf_per_doc[w].items():
                    pl[new_document] = term_frequency
                self.count[w] = (
                    self.count[w][0] + len(tf_per_doc[w]),
                    self.inverse_document_freq(self.count[w][0] + len(tf_per_doc[w]))
                )

            pl_len = 0
            for document, term_frequency in pl.items():
                pl_len += self.write_pl_row(document, term_frequency * self.count[w][1], temp_path)
            self.voc[w] = (pl_len, pl_offset)
            pl_offset += pl_len

        # iterate in tf_per_doc for words not in voc
        for w in tf_per_doc:
            if w not in self.voc:
                #               count of docs the word shows up in, idf
                self.count[w] = (len(tf_per_doc[w]), self.inverse_document_freq(len(tf_per_doc[w])))
                pl_len = 0
                for new_document, term_frequency in tf_per_doc[w].items():
                    pl_len += self.write_pl_row(new_document, term_frequency * self.count[w][1], temp_path)
                self.voc[w] = (pl_len, pl_offset)
                pl_offset += pl_len

        self.finalize_merge_pl(temp_path, self.path)
        return

    @staticmethod
    def extract_data(raw_document_path, files_indexed):
        texts = {}
        with open(raw_document_path, "r") as file:
            text = ""
            for line in file:
                text += line
            text = "<DOCCOLLECTION>" + text + "</DOCCOLLECTION>"

            docs = ElTree.fromstring(text)

            articles_indexed = 0
            for article in docs:
                doc_id = int(article.find('./DOCID').text.strip()) + (files_indexed * (10 ** 6))

                # print("Adding document {} from file {} to index".format(doc_id, filename))
                important_stuff = Index.get_element_inner_text(article, './HEADLINE') + '\n' \
                    + Index.get_element_inner_text(article, './BYLINE') + '\n' \
                    + Index.get_element_inner_text(article, './TEXT') + '\n' \
                    + Index.get_element_inner_text(article, './SUBJECT') + '\n' \
                    + Index.get_element_inner_text(article, './GRAPHIC') + '\n'

                # TODO save (reference?) to original document
                # Lowercase as early as possible, reduces amount of calls
                # important_stuff = important_stuff.lower()
                texts[doc_id] = important_stuff
                articles_indexed += 1
        return texts


    def apply_word_filters(self, value):
        for f in self.word_filters:
            value = f.prepare_word(value)

        return value


    def process_files(self, files):
        files_indexed = 0
        # Dictionary of term frequencies per word per doc

        tf_per_doc = {}
        for filename in files:
            for doc_id, text in Index.extract_data(filename, files_indexed).items():
                # Remove punctuation from words
                self.documents_content[doc_id] = text
                #The maximum frequency of a word in the doc
                max_freq = 1

                for filter in self.line_filters:
                    text = filter.prepare_line(text)
                words = text.split(" ")
                words = [self.apply_word_filters(x) for x in words]
                words = [x for x in words if not x == ""]

                for w in words:
                    # Set up dictionary
                    if w not in tf_per_doc:
                        tf_per_doc[w] = {}
                    if doc_id not in tf_per_doc[w]:
                        tf_per_doc[w][doc_id] = 0
                    tf_per_doc[w][doc_id] += 1
                    if tf_per_doc[w][doc_id] > max_freq:
                        max_freq = tf_per_doc[w][doc_id]
                # Calculate tf for each entry
                for w in words:
                    tf_per_doc[w][doc_id] = Index.term_frequency(tf_per_doc[w][doc_id], max_freq)

                self.docs_indexed += 1

            files_indexed += 1
        return tf_per_doc

    def print_index_stats(self):
        print("Words in index")
        print(len(self.voc))
        print('====')
        print(self.docs_indexed)
        # TODO MOOOORE


class Searcher:
    def __init__(self, index, line_filters, word_filters):
        self.index = index
        self.word_filters = word_filters
        self.line_filters = line_filters

    def prepare_query(self, query):
        for filter in self.line_filters:
            query = filter.prepare_line(query)

        seperated_words = query.split(" ")

        for i in range(len(seperated_words)):
            for filter in self.word_filters:
                seperated_words[i] = filter.prepare_word(seperated_words[i])

        return " ".join(seperated_words)


    def search(self, word_list):
        pl = {}
        for a_word in word_list:
            if a_word.find('&') > -1:
                conjonctive_part = a_word.split('&')
                #initialise the pl with the first word
                if conjonctive_part[0] in self.index.voc:
                    conj_pl = self.index.read_pl_for_word(*(self.index.voc[conjonctive_part[0]]), self.index.path)
                else:
                        print(conjonctive_part[0]+" : Word not found")
                        break
                for i in range(1, len(conjonctive_part)):
                    if conjonctive_part[i] in self.index.voc:
                        # make the intersection of the documents found for all words of the conjonctive query
                        found_pl = self.index.read_pl_for_word(*(self.index.voc[conjonctive_part[i]]), self.index.path)
                        intersect = {}
                        keys_a = set(conj_pl.keys())
                        keys_b = set(found_pl.keys())
                        intersect_keys = keys_a & keys_b
                        for item in intersect_keys:
                            intersect.update({item : found_pl[item] + conj_pl[item]})
                        conj_pl = intersect
                    else:
                        print(conjonctive_part[i]+" : Word not found")
                        conj_pl.clear()
                        break
                pl.update(conj_pl)
            elif a_word in self.index.voc:
                found_pl = self.index.read_pl_for_word(*(self.index.voc[a_word]), self.index.path)
                for document, score in found_pl.items():
                    if document not in pl:
                        pl[document] = 0
                    pl[document] += score
            else:
                print(a_word+" : Word not found")
        if not bool(pl):
            print("No document found")
        pl = sorted(pl.items(), key=lambda kv: kv[1], reverse=True)
        for document, score in pl:
            print('Document: ', document, '---', 'Score: ', score)

    def knn(self, doc, k):
        #take the words out of the document
        doc_pl = {}
        for word in self.index.voc:
            found_pl = self.index.read_pl_for_word(*(self.index.voc[word]), self.index.path)
            if doc in found_pl.keys():
                doc_pl.update({word: found_pl[doc]})
        pl = {}
        for a_word in doc_pl.keys():
            found_pl = self.index.read_pl_for_word(*(self.index.voc[a_word]), self.index.path)
            for document, score in found_pl.items():
                if document != doc:
                    if document not in pl:
                        pl[document] = 0
                    pl[document] += score * doc_pl[a_word]
        pl = sorted(pl.items(), key=lambda kv: kv[1], reverse=True)
        count = 0
        for document, score in pl:
            print('Document: ', document, '---', 'Score: ', score)
            count += 1
            if count == k:
                break

def main():
    parser = argparse.ArgumentParser(description='Text indexing',
                                     epilog='Written for the INSA Lyon text-indexing Project by Anh Pham, Mathilde du Plessix, '
                                            'Romain Latron, Beonît Zhong, Martin Haug. 2018 All rights reserved.')

    parser.add_argument('pl', help='Posting list location')
    parser.add_argument('--eval', default=None, help='Used to eval indexing')
    parser.add_argument('-b','--batch', type=int, default=10, help='Define the batch size')
    args = parser.parse_args()

    if len(sys.argv) < 2:
        print("Please specify the name for the posting list file in an argument")
        print("Usage example: {} ./data/pl-file".format(sys.argv[0]))
        exit(-1)

    path = args.pl
    batch_size = args.batch
    eval = args.eval



    m = re.search('((?<=^["\']).*(?=["\']$))', path)
    if m is not None:
        path = m.group(0)

    line_filters = [LowercasePreparation(), DeleteCharacterPreparation()]
    word_filters = [StemmingPreparation()]
    # Get a instance of our index and search
    index = Index(path, line_filters, word_filters)
    searcher = Searcher(index, line_filters, word_filters)
    # Prepare the RegEx to find numbers in our user input
    int_find = re.compile('\d+')

    if eval:
        index.index_folder(eval, batch_size)
        exit(0)
    print("\nWelcome to the research engine")
    print("==============================")
    # Return to the menu after tasks were accomplished
    while True:
        print("\nWhat would you like to do?")
        print("1) Add a folder of documents to the index")
        print("2) Do a search query")
        print("3) Show stats about the index")
        print("4) Look for similar documents")
        print("5) Read a document")
        print("6) Exit")
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
            index.index_folder(folder, batch_size)
        elif menu_item == 2:
            while True:
                search_query = input('\nType :read to display a document or :quit to return to menu\nPlease enter your search query: ')
                if search_query == ":quit":
                    break
                elif search_query == ":read":
                    doc_id = input('Please enter the document id: ')
                    print(index.documents_content[int(doc_id)])
                else:
                    searcher.search(search_query.split())


        elif menu_item == 3:
            index.print_index_stats()
        elif menu_item == 4:
            while True:
                search_query = input('\nType :read to display a document or :quit to return to menu\nPlease enter your document:  ')
                if search_query == ":quit":
                    break
                elif search_query == ":read":
                    doc_id = input('Please enter the document id: ')
                    print(index.documents_content[int(doc_id)])
                else:
                    k = input('Please enter the number of documents you want: ')
                    searcher.knn(int(search_query), int(k))
        elif menu_item == 5:
            doc_id = input('Please enter the document id: ')
            print(index.documents_content[int(doc_id)])
        elif menu_item == 6:
            exit(0)
        else:
            print("Unknown menu item")


if __name__ == "__main__":
    main()
