from timer import Timer
import numpy

class Searcher:
    def __init__(self, index, line_filters, word_filters):
        self.index = index
        self.word_filters = word_filters
        self.line_filters = line_filters

    def prepare_query(self, query):
        for line_filter in self.line_filters:
            query = line_filter.prepare_line(query)

        separated_words = query.split(" ")

        for i in range(len(separated_words)):
            for line_filter in self.word_filters:
                separated_words[i] = line_filter.prepare_word(separated_words[i])

        return " ".join(separated_words)

    def search(self, word_list, verbose=True):
        timer = Timer()
        timer.start()
        pl = {}
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
        output = -1
        timer.stop()
        time_tuple = timer.get_duration_tuple()
        if verbose:
            print("Query returned in {}s {}ms".format(time_tuple[1], time_tuple[2]))

        for document, score in pl:
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

    def similarWord(self, word, k):
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



