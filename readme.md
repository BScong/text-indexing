# Text Indexing

## Goal
The goal of this project is to index every word from a large set of documents, in order to perform searches on them (simple, conjunctive, disjunctive searches), sorted by relevance.

## Usage
`python3 main.py [-h] [--eval EVAL] [-b BATCH] [-l] [-s] [--stem] [--progress-bar] pl_file_path`
You have to execute `main.py` by giving it a path for the Posting List file. It overrides it by default.

Options:
 - `-l`,`--load`: load the current Posting List and vocabulary. The vocabulary is stored at path (`pl_file_path+'_voc'`).
 - `--eval`: used to measure batch processing times. Need to specify a folder to index as a parameter.
 - `-b`,`--batch`: to specify a batch size.
 - `-s`, `--stopwords`: ignore english stopwords while indexing or index with stopwords ignored used
 - `--stem`: use stemming
 - `--progress-bar`: show a progress bar while indexing

## Principle

### Vocabulary and Posting List
The system is based on a vocabulary (that can fit into memory) and posting lists. The Vocabulary contains every word seen in documents and maps them to an offset in the posting list.
The posting list is a binary file saved on the disk. For each word, it contains the (document_id, score) tuple.

### Score
The score is a value that we compute for each word, for each document. It stands for the relevance of that word in that document, the higher it is, the more relevant that word is for that document.

#### Computing scores
The score is computed with a TF-IDF algorithm.
The TF is computed with the formula `1 + math.log10(number_occurences)`.
The IDF is computed with the formula `math.log10(total_number_of_docs / (1 + number_of_docs_containing_word))`.

### Merge-based algorithm
To build the Posting List, we must implement a merge-based algorithm.

This algorithm relies on several things:
-   We treat documents as batches
-   We keep the entire vocabulary in the memory
-   Only one posting list is valid at a time t
-   A temporary posting list is kept in memory

For each batch, we build a posting list in memory. When this PL is built, we merge it to the PL on disk (or we save it if it's the first batch). For the merge process, we iterate on the vocabulary and merge both lines (PL on disk and PL in memory if present). We then update the offset in the vocabulary and move to the next word. In the end, we iterate on the PL on memory to add new words that are not yet present in the vocabulary.

This architecture is not very efficient for distributed computing as we need to merge the files after each batch. The optimal solution for a distributed environment is to generate all the files for each batch on a first phase, then merge them on a second phase.

### Stemming

Stemming is also implemented to regroup words from the same semantic family.

### Search documents with a word

- Naive approach:
The research can be done in a disjunctive way (one of the words have to be in the documents) or conjunctive way (all the words have to be in documents).
To research documents in a conjunctive way, you have to put '&' between the words, without anything it will be a disjunctive search.
The result of the search show documents ordered by their score which is the sum of the scores for each word.

- Fagin's top k algorithm:
This algorithm is used for conjunctive search (search can be done with '&' or without it) and returns the top k documents that contain the words in the request.
The result of the search show documents ordered by their score which is the average (summing the scores of the documents in their respective PL and dividing it by the number of words).

This algorithm is slower than the naive approach, it can be explained by several factors:
- It starts with sorting the PL of each requested words by their score, the more a word appears in a lot of document, the more it's time-consuming
- In the last part, it has to browse each document that has been added in M, and check whether the document has been seen in all the PL. This process can take some time when the request is made of many words and when each respective word does not appear in every document. As a result, M can contain many documents which presence has to be checked in all the PL.

### Search k nearest neighbors for a document

The request takes an id of a document as a parameter, then looks all over the PL for the words that are contained in the document. Then,
we make the sum of the products of the scores of the matching words of the document for every document in the base, and we display the k documents with the highest score.
It is actually similar to a scalar product, with vectors representing the score of the words in the dictionary for each document.

### Semantically similar words

We implemented an option to search for semantically similar words to a given word. When we process the files, we create a 200 digits vector for each document, with four +1 and four -1 randomly located, and the rest filled with zeros. Each word has a context vector of the same size, 200, initialized at 0. Then, each time a word is contained in a document, we add the document vector to the context vector of the word, and we normalize it.
This way, when we enter a word as a parameter, the program makes a scalar product between the context vector of the word and all words of the dictionary (similar to a cosine function because the vectors are normalized) and returns the k words with the highest score.


## Benchmark
The following benchmarks have been made on the entire dataset (131896 documents in 730 files).

### Indexing
We wanted to see the impact of the size of each batch on memory consumption and running time.

![Plot of running time depending on batch size](https://github.com/BScong/text-indexing/blob/master/benchmark/measures_1_clean/time.png)


![Plot of maximum memory consumption depending on batch size](https://github.com/BScong/text-indexing/blob/master/benchmark/measures_1_clean/memory.png)

Here, we can see that we have an inflexion point at around 200/300 for the batch size, that would be an optimal batch size (assuming we have enough memory), as all the batch sizes above that number take approximately the same time to index.
We can also see that there is threshold for the batch size, above that threshold the memory consumption caps but the process doesn't take longer to run. That may be due to a memory limit set for programs on the OS used to run the benchmark. Also, the computer used for the benchmark had SSDs as hard drives, we suppose that this may be the reason to why the running time was not increased that much.

### Search
![Plot of request time depending on length of conjonctive request](https://github.com/BScong/text-indexing/blob/master/benchmark/search_benchmark.png)

In this benchmark we can see that the naive approach performs better than Fagin's algorithm mainly due to the two points that have been mentionned in the explanation of the algorithm. Due to lack of time, we were not able to tackle the problem of the performance of OrderedDict(), which in our measurements took almost half the time of the algorithm. Solving this problem could cut down the request time significantly. Also, optimizing the parallel access to the PL could be another factor that could improve the algorithm's performance.
