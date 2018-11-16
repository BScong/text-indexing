import sys
import re

from index import Index
from search import Searcher
import text_preprocessing
from doc_utils import Reader


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

    line_filters = text_preprocessing.get_instances_of_all_line_preparators()
    word_filters = text_preprocessing.get_instances_of_all_word_preparators()
    # Get a instance of our index and search
    index = Index(path, line_filters, word_filters)
    searcher = Searcher(index, line_filters, word_filters)
    # Prepare the RegEx to find numbers in our user input
    int_find = re.compile('\d+')

    path_current = ""
    reader = None
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

            path_current = folder
            index.index_folder(folder)
            reader = Reader(path_current)

        elif menu_item == 2:
            default = -1
            while True:
                search_query = input('\nType :read to display a document or :quit to return to menu'
                                     '\nPlease enter your search query: ')
                if search_query == ":quit":
                    break
                elif search_query == ":read":
                    doc_id = input('Please enter the document id{}: '
                                   .format("" if default < 0 else " ({})".format(default))).strip()
                    if doc_id == "" and default >= 0:
                        doc_id = default
                    print(reader.read_doc(int(doc_id)))
                else:
                    default = searcher.search(search_query.split())

        elif menu_item == 3:
            index.print_index_stats()

        elif menu_item == 4:
            while True:
                search_query = input('\nType :read to display a document or :quit to return to menu'
                                     '\nPlease enter your document:  ')
                if search_query == ":quit":
                    break
                elif search_query == ":read":
                    doc_id = input('Please enter the document id: ')
                    print(reader.read_doc(int(doc_id)))
                else:
                    k = input('Please enter the number of documents you want: ')
                    searcher.knn(int(search_query), int(k))

        elif menu_item == 5:
            doc_id = input('Please enter the document id: ')
            print(reader.read_doc(int(doc_id)))

        elif menu_item == 6:
            exit(0)

        else:
            print("Unknown menu item")


if __name__ == "__main__":
    main()
