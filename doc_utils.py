import xml.etree.ElementTree as ElTree
from os import listdir
from os.path import isfile, join


def get_element_inner_text(element, xpath):
    if element is None:
        return ""
    found = element.find(xpath)
    if found is None:
        return ""
    return "".join(found.itertext())


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
            important_stuff = get_element_inner_text(article, './HEADLINE') + '\n' \
                              + get_element_inner_text(article, './BYLINE') + '\n' \
                              + get_element_inner_text(article, './TEXT') + '\n' \
                              + get_element_inner_text(article, './SUBJECT') + '\n' \
                              + get_element_inner_text(article, './GRAPHIC') + '\n'

            # Lowercase as early as possible, reduces amount of calls
            # important_stuff = important_stuff.lower()
            texts[doc_id] = important_stuff
            articles_indexed += 1
    return texts


class Reader:
    def __init__(self, folder_name):
        # check if folder_name is folder
        self.folder_name = folder_name + '/' if folder_name[-1] != '/' else folder_name

    def read_doc(self, doc_id):
        file_index = doc_id // 10 ** 6
        doc_id = doc_id - file_index * 10 ** 6

        files = [self.folder_name + f for f in listdir(self.folder_name)
                 if isfile(join(self.folder_name, f)) and 'la' in f]

        arr = extract_data(files[file_index], 0)
        return arr[doc_id]
