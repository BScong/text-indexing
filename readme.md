# Text Indexing

## Goal
The goal of this project is to index every word from a large set of documents, in order to perform searches on them (simple, conjonctive, disjonctive searches), sorted by relevance.

## Usage
`python3 main.py [-h] [--eval EVAL] [-b BATCH] [-l] pl_file_path`
You have to execute `main.py` by giving it a path for the Posting List file. It overrides it by default.

Options:
 - `-l`,`--load`: load the current Posting List and vocabulary. The vocabulary is stored at path (`pl_file_path+'_voc'`).
 - `--eval`: used to measure batch processing times. Need to specify a folder to index as a parameter.
 - `-b`,`--batch`: to specify a batch size.

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

For each batch, we build a posting list in memory. When this PL is built, we merge it to the PL on disk (or we save it if it's the first batch). For the merge process, we iterate on the vocabulary and merge both lines (PL on disk and PL in memory if present). We then update the offset in the vocabulary and move to the next word. At the end, we iterate on the PL on memory to add new words that are not yet present in the vocabulary.

This architecture is not very efficient for distributed computing as we need to merge the files after each batch. The optimal solution for a distributed environment is to generate all the files for each batch on a first phase, then merge them on a second phase.

### Stemming
Stemming is also implemented to regroup words from the same semantic family.

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
