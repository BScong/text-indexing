import io
from collections import OrderedDict
import struct
import os
from os import listdir
from os.path import isfile, join
import math
import statistics
from timer import Timer
import doc_utils


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

    @staticmethod
    def term_frequency(count_doc_occurrences, max_freq):
        # see slide 8
        if count_doc_occurrences == 0:
            return 0

        return 0.5 + 0.5 * count_doc_occurrences / max_freq

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

    def index_folder(self, folder_name, batch_size=10):
        # Open files from specified folder
        timer = Timer()
        timer.start()
        try:
            prev_index = self.docs_indexed
            # check if folder_name is folder
            if folder_name[-1] != '/':
                folder_name = folder_name + '/'

            files = [folder_name + f for f in listdir(folder_name) if isfile(join(folder_name, f)) and 'la' in f]

            timer.round()
            for i in range(0, len(files), batch_size):
                tfs = self.process_files(files[i:min(i + batch_size, len(files))])

                self.merge_save(tfs)
                timer.round()

                """terminal.print_progress(min(i + batch_size, len(files)),
                                        len(files),
                                        prefix='Adding files: ',
                                        suffix='Complete',
                                        bar_length=80)"""

            timer.stop(last_round=False)
            batch_times = timer.get_round_durations()
            batch_times.pop(0)

            print("Indexed {} documents in {} files during {} batches. Total elapsed time \t {:02d}m {:02d}s {:03d}ms"
                  .format(self.docs_indexed - prev_index, len(files), len(batch_times), *(timer.get_duration_tuple())))
            print("Minimum batch time: \t {:02d}m {:02d}s {:03d}ms".format(*Timer.time_to_tuple(min(batch_times))))
            print("Maximum batch time: \t {:02d}m {:02d}s {:03d}ms".format(*Timer.time_to_tuple(max(batch_times))))
            print("Average batch time: \t {:02d}m {:02d}s {:03d}ms"
                  .format(*Timer.time_to_tuple(statistics.mean(batch_times))))
            print("Median  batch time: \t {:02d}m {:02d}s {:03d}ms"
                  .format(*Timer.time_to_tuple(statistics.median(batch_times))))
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
                    pl[old_document] = pl[old_document] / self.count[w][1] \
                        if self.count[w][1] != 0 else pl[old_document]

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

    def apply_word_filters(self, value):
        for f in self.word_filters:
            value = f.prepare_word(value)

        return value

    def process_files(self, files):
        files_indexed = 0
        # Dictionary of term frequencies per word per doc

        tf_per_doc = {}
        for filename in files:
            for doc_id, text in doc_utils.extract_data(filename, files_indexed).items():
                # Remove punctuation from words
                # The maximum frequency of a word in the doc
                max_freq = 1

                for filter_tool in self.line_filters:
                    text = filter_tool.prepare_line(text)
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
