import xml.etree.ElementTree as ElTree
from os import listdir
from os.path import isfile, join


def get_indexable_filenames(folder_name):
    return sorted([folder_name + f for f in listdir(folder_name)
                 if isfile(join(folder_name, f)) and 'la' in f])

def get_element_inner_text(element, xpath):
    if element is None:
        return ""
    found = element.find(xpath)
    if found is None:
        return ""
    return "".join(found.itertext())

def file_to_xml(file_path):
    with open(file_path, "r") as file:
        text = ""
        for line in file:
            text += line
        text = "<DOCCOLLECTION>" + text + "</DOCCOLLECTION>"
        return ElTree.fromstring(text)


def extract_data(raw_document_path, files_indexed):
    texts = {}
    docs = file_to_xml(raw_document_path)
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


def title_of_doc(doc_no, file_path, all=False, max_char=60, pad=False):
    tree = file_to_xml(file_path)
    title = str(doc_no)
    for article in tree:
        if int(article.find('./DOCID').text.strip()) != doc_no:
            continue
        title = get_element_inner_text(article, './HEADLINE').strip().title()
        break
    newline_array = title.split('\n')
    title = newline_array[0]
    if all:
        title = " ".join(newline_array)
    if 3 < max_char < len(title):
        stripped_title = title[:max_char - 3].strip()
        end_space_present = (len(stripped_title) - len(title[:max_char - 3])) > 0
        title = title[:max_char - 3].strip() + ('....' if end_space_present else '...')
    if pad and max_char > 3 and len(title) < max_char:
        title += ' ' * (max_char - len(title))
    return title

class Reader:
    def __init__(self, index):
        # check if folder_name is folder
        self.index = index

    def split_file_doc_id(self, doc_id):
        interim_id = doc_id // 10 ** 6
        article_id = doc_id - interim_id * 10 ** 6

        biggest_matching = {'name': None, 'offset': float("-inf")}
        for directory in self.index.directories:
            if directory['offset'] > interim_id:
                break

            if directory['offset'] > biggest_matching['offset']:
                biggest_matching = directory

        file_index = interim_id - biggest_matching['offset']

        return biggest_matching['name'], file_index, article_id

    def get_doc_title(self, doc_id):
        folder_name, file_index, doc_id = self.split_file_doc_id(doc_id)

        files = get_indexable_filenames(folder_name)

        return title_of_doc(doc_id, files[file_index], pad=True)

    def read_doc(self, doc_id):
        folder_name, file_index, doc_id = self.split_file_doc_id(doc_id)

        files = get_indexable_filenames(folder_name)

        arr = extract_data(files[file_index], 0)
        return arr[doc_id]
