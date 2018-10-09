from os import listdir
from os.path import isfile, join
import re

words = {}

def indexFolder(folder_name):
    files = [f for f in listdir(folder_name) if isfile(join(folder_name, f))]

    for f in files:
        text = open('./data/subset/' + f, "r")
        n_words = 0
        for line in text:
            # Remove tags
            line = re.sub('<.+?>', ' ', line)
            # Remove punctuation from words
            for w in re.split('[\. ()\[\],:;]', line):
                w = w.lower()
                n_words += 1
                if w not in words:
                    words[w] = {}
                if f not in words[w]:
                    words[w][f] = 0
                words[w][f] += 1
        for w in words:
            if f in words[w]:
                words[w][f] = words[w][f]/n_words

    print(words['the'])


def printIndexStats():
    print("Words in index")
    print(len(words))

def main():
    print("\nWelcome to the research engine")
    print("==============================")

    int_find = re.compile('\d+')

    while True:
        print("\nWhat would you like to do?")
        print("1) Add a folder of documents to the index")
        print("2) Do a search query")
        print("3) Show stats about the index")
        print("4) Exit")
        print("\n Please enter the number of a menu item")

        user_choice = input('> ')
        print("")
        menu_item = int_find.search(user_choice)

        if menu_item == None:
            print("No number found")
            continue

        menu_item = int(menu_item.string)

        if menu_item == 1:
            default = './data/subset/'
            print("Please enter the folder's path")
            folder = input('({}) > '.format(default)).strip()
            if folder == "":
                folder = default
            indexFolder(folder)
        elif menu_item == 2:
            pass
        elif menu_item == 3:
            printIndexStats()
        elif menu_item == 4:
            exit(0)
        else:
            print("Unknown menu item")

if __name__ == "__main__":
    main()