# Text Indexing

## Goal
The goal of this project is to index every word from a large set of documents, in order to perform searches on them (simple, conjonctive, disjonctive searches), sorted by relevance.

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

### Stemming
Stemming is also implemented to regroup words from the same semantic family.
