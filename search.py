from timer import Timer
from collections import OrderedDict

import numpy


class Searcher:
    def __init__(self, index):
        self.index = index

    def prepare_query(self, query):
        for line_filter in self.index.line_filters:
            query = line_filter.prepare_line(query)

        separated_parts = query.split("&")
        for i in range(len(separated_parts)):
            separated_parts[i] = separated_parts[i].split(" ")
            for j in range(len(separated_parts[i])):
                for line_filter in self.index.word_filters:
                    separated_parts[i][j] = line_filter.prepare_word(separated_parts[i][j])
            separated_parts[i] = " ".join(separated_parts[i])

        return "&".join(separated_parts)

    def search(self, word_list, verbose=True):
        timer = Timer()
        timer.start()
        pl = {}
        word_list = self.prepare_query(word_list).split()
        for a_word in word_list:
            if a_word.find('&') > -1:
                conjunctive_part = a_word.split('&')
                # initialise the pl with the first word
                if conjunctive_part[0] in self.index.voc:
                    conj_pl = self.index.read_pl_for_word(*(self.index.voc[conjunctive_part[0]]), self.index.path)
                else:
                    print(conjunctive_part[0] + " : Word not found")
                    break
                for i in range(1, len(conjunctive_part)):
                    if conjunctive_part[i] in self.index.voc:
                        # make the intersection of the documents found for all words of the conjunctive query
                        found_pl = self.index.read_pl_for_word(*(self.index.voc[conjunctive_part[i]]), self.index.path)
                        intersect = {}
                        keys_a = set(conj_pl.keys())
                        keys_b = set(found_pl.keys())
                        intersect_keys = keys_a & keys_b
                        for item in intersect_keys:
                            intersect.update({item: found_pl[item] + conj_pl[item]})
                        conj_pl = intersect
                    else:
                        print(conjunctive_part[i]+" : Word not found")
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
        output = []
        timer.stop()
        time_tuple = timer.get_duration_tuple()
        if verbose:
            print("Query returned in {}s {}ms".format(time_tuple[1], time_tuple[2]))

        for document, score in pl:
            output.append({'document': document, 'score': score})
        return output

    def search_fagins(self, word_list, k, verbose=True):
        timer = Timer()
        timer.start()
        word_list = self.prepare_query(word_list).split()
        print(word_list)
        pl_list = {}
        line = 0
        c = {}
        m = {}
        min_length = 100
        i = 0

        # for conjunctive query, if a word is not found then no documents are returned
        for a_word in word_list:
            if a_word.find('&') > -1:
                conjunctive_part = a_word.split('&')
                for j in range(0, len(conjunctive_part)):
                    if conjunctive_part[j] in self.index.voc:
                        pl_list[i] = OrderedDict(
                            sorted(self.index.read_pl_for_word(*(self.index.voc[conjunctive_part[j]]),
                                   self.index.path).items(),
                                   key=lambda t: t[1], reverse=True))
                        if len(pl_list[i]) < min_length:
                            min_length = len(pl_list[i])
                        i += 1
                    else:
                        print(conjunctive_part[j] + " : Word not found")
                        print("No documents found")
                        return
            # disjunctive query
            else:
                if a_word in self.index.voc:
                    pl_list[i] = OrderedDict(
                        sorted(self.index.read_pl_for_word(*(self.index.voc[a_word]),
                                                           self.index.path).items(),
                               key=lambda t: t[1], reverse=True))
                    if len(pl_list[i]) < min_length:
                        min_length = len(pl_list[i])
                    i += 1
                else:
                    print(a_word + " : Word not found")

        # stops when C has k elements or we finished going through all the lines of pl
        while line < min_length and len(c) < k:
            i = 0
            while i < len(pl_list):
                # iterate on each line of each pl
                if line < len(pl_list[i]):
                    doc_id = list(pl_list[i])[line]
                    if doc_id in m.keys():
                        old_score = m[doc_id][0]
                        m[doc_id][1].append(i)
                        m[doc_id] = (((old_score + pl_list[i][doc_id]) / len(m[doc_id][1])), m[doc_id][1])
                        if len(m[doc_id][1]) == len(pl_list):
                            c[doc_id] = m[doc_id][0]
                            del m[doc_id]
                    else:
                        # In M: doc_id -> (score, list of pl)
                        pl_visited = list()
                        pl_visited.append(i)
                        m[doc_id] = (pl_list[i][doc_id], pl_visited)
                i += 1
            line += 1

        for doc in m.keys():
            temp_score = m[doc][0]
            temp_length = len(m[doc][1])
            for i in range(0, len(pl_list)):
                if i not in m[doc][1]:
                    if doc in pl_list[i]:
                        temp_score = ((temp_score * temp_length) + pl_list[i][doc]) / (temp_length + 1)
                        temp_length += 1
                    # score set to 0 when doc not in pl
                    else:
                        temp_score = temp_score * temp_length / (temp_length + 1)
                        temp_length += 1

            # check if current doc is in all posting lists and its score is greater than min score in C
            if c:
                if temp_score > min(c.values()) and len(c) == k:
                    min_entry = min(c, key=c.get)
                    del c[min_entry]
                    c[doc] = temp_score
                # case where C not full yet
                elif len(c) < k:
                    c[doc] = temp_score
            # if c is empty
            else:
                c[doc] = temp_score

        c = OrderedDict(sorted(c.items(), key=lambda t: t[1], reverse=True))
        output = -1
        timer.stop()
        time_tuple = timer.get_duration_tuple()
        if verbose:
            print("Query returned in {}s {}ms".format(time_tuple[1], time_tuple[2]))

        for document, score in c.items():
            if output < 0:
                output = document
            print('Document: ', document, '---', 'Score: ', score)
        return output

    def knn(self, doc, k, verbose=True):
        # take the words out of the document
        timer = Timer()
        timer.start()
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
        timer.stop()
        time_tuple = timer.get_duration_tuple()
        if verbose:
            print("Query returned in {}s {}ms".format(time_tuple[1], time_tuple[2]))

        for document, score in pl:
            print('Document: ', document, '---', 'Score: ', score)
            count += 1
            if count == k:
                break

    def similar_word(self, word, k):
        word = self.prepare_query(word)
        if word not in self.index.voc:
            print("Word not found")
            return
        context_vec = self.index.context_vectors[word]
        word_scores = {}
        for w in self.index.voc:
            word_scores[w] = numpy.dot(self.index.context_vectors[w], context_vec)
        word_scores[word] = 0
        word_scores = sorted(word_scores.items(), key=lambda kv: kv[1], reverse=True)
        count = 0
        for w, score in word_scores:
            print(w, '---', 'Score: ', score)
            count += 1
            if count == k:
                break
