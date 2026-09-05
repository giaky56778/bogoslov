# BogoSlov

Biblical OriGins in slavOnic texts - Systems for Language-modelled Observation and Verification

A [SEED4EU+](https://4euplus.eu/4EU-1150.html) project. For further information, see (Ruskov et al 2025).

The contained corpora are courtesy to:

* Bologna Psalter: digitalisation by [Mary Catherine MacRobert](https://www.some.ox.ac.uk/our-people/catherine-mary-macrobert/), transliteration from Latin to Cyrillic by Martin Ruskov, TEI annotation by Martin Ruskov, Lemmatization with [UDPipe](https://lindat.mff.cuni.cz/services/udpipe/).

* Sinai Psalter, Codex Marianus, Codex Zographensis: [XSLT transformed](static/proiel2tei.xsl) from the [Syntacticus project](https://github.com/syntacticus/syntacticus-treebank-data). This source is aligned with the [Universal Dependencies](https://universaldependencies.org/) initiative and thus contains annotations, including human-validated lemmatization.

The BukyVede font is courtesy to [Kempgen and others](https://kodeks.de/AKSL/Schrift/BukyVedeBackground.htm).

# Architecture
```WebSequenceDiagrams.com
title Process Flow

User->WebInterface: Open Page
User->WebInterface: Choose Tool
User->Tool: Enter Query
Tool->DB: Get Primary Sources and their Representation
DB-->Tool: Primary Sources and Representation
Tool->Tool: Calculate Representation of Query
Tool->DB: Compare Query to Primary Sources
DB-->Tool: List of results
Tool->User: List of results
```

# Installation

Requirements [python](https://www.python.org) and [docker compose](https://docs.docker.com/compose).

## Language support

A starting point for a new setup is the choice of language. This is relevant for the corpora and the database derived from them. To support a language the following are needed: alphabet.${CORPUS_LANG}.tsv (for examples see [slavonic](static/alphabet.chu.tsv) and [latin](static/alphabet.lat.tsv)) and a lang_.${CORPUS_LANG}.py. For this you would need to specify HuggingFace and [UDPipe](https://lindat.mff.cuni.cz/services/udpipe/) models. Currently, `chu`, `lat` and `grc` are supported. Finally, a `static/${CORPUS_LANG}.css` is needed in case historical fonts are preferred.

## Preparing the data {#datapreparation}

Specify the language you are working with in `.env`. 

Make sure you have docker compose installed. We get started by creating the container image that will be used to deploy In the `code` directory run

    docker build -t bogoslov .

Then in the root directory initialize the data with (potentially changing the env file)

    docker compose --env-file env.chu -f compose-init.yml up --abort-on-container-exit --exit-code-from populate


If you need to deploy to a machine where you cannot run the initialization scripts, make sure to export your data on a *nix environment with (making sure to enable the lines for the correct language):

    ./dump-db.sh

Then make sure to have the exported files in the init directory of your deployment at the first launch of your `db` container.

## Running

After having initialized the data, run (selecting the env file of choice):

    docker compose --env-file env.chu up

Open http://localhost:8780 with your browser.

# Corpora

The N-gram approach relies on lemmatisation. This is the reason why we prefer adopting texts from treebanks, and PROIEL and its sister projects in particular. In such treebanks lemmatisation was manually verified. Automatic lemmatization is used for other corpora, but due to variation in historical languages, this is less reliable.

## Adding a new corpus

New corpora need to be lemmatized. We use TEI as a representation of a lemmatized text. If your source is in another format, you would need to convert it. Example XSLT transformations for sources from PROIEL are available in the `static/` directory. If you do not have lemmatized data, you could use an automatic lemmatizer like UDPipe.

To use the data, it needs to be available in .html format for viewing (see the corresponding [XSLT transformation](static/tei2html.xsl)). For performance reasons, it also needs to be imported as explained in the [Preparing the data](#datapreparation). It also needs to be included in the corresponding `lang_*.py`, see e.g. [lang_chu.py](https://github.com/mapto/bogoslov/blob/main/src/lang_chu.py#L8).

# Algorithms

It is important to note that due to the specifics of biblical texts, we consider verses as the units of meaning. This means that we tokenise by verses and do not consider potential matches that cross verse boundaries. We do not 

## Regex - regular expresssions

This approach aims to address orthographic variation through the explicit definition of orthographic equivalences. Here we use tables with tab-separated values. A first such table for Old Church Slavonic was originally proposed to us by Achim Rabus. 

Regular expressions consider as mutually exchangeable explicitly defined character or phonemes expressed through combinations of character. Due to this, the approach is suitable for searching of similarity to short texts, typically one or two words, as they tend to get overly complex for longer sequences. Because of this limitation, this approach could be seen as a complement to N-grams.

We have not defined a useful accuracy function for regular expressions. That's why it is seen as binary: a match gets an accuracy score of 1.0 and the absence of match is scored as 0.

## N-gram - lemmatised N-gram search

In this approach we adopt lemmatisation as a way of normalising orthography. This exploits the fact that lemmatisation is designed to reduce excess orthographic variation. This approach was brought to the project by Tomáš Mikulka, based on his experience with similar functionality in Thesaurus Linguae Graecae.

Naturally, when talking of lemmatisation, the unit of analysis are words. The n-gram approach yields better results for 3-grams and higher values of N. This automatically means that it cannot be used for searching of similarity to texts consisting of less than N tokens. As a consequence this approach complements well the regex approach.

The formula to calculate accuracy is the number of matching N-grams, over the total number of N-grams in the search text.

## LCS - Longest common subsequence

The longest common subsequence is a commonplace computer science algorithm with a broad range of applications, such as bioinformatics. Martin Ruskov has identified it as a potentially good candidate for the challenges of quotation identification in Old Church Slavonic. This intuition has been confirmed by other researchers who successfully used and evaluated it in other contexts.

This is a purely syntactic approach which does not look at specific cooccurences of character, but looks for general similarity between two strings. Although it could be applied at words as a level of analysis, due to orthographic variation, this is expected to be less advantageous. Thus we apply it at che character level.

Accuracy is calculated as twice the length of the longest common subsequence over the combined length of the search string and the shortest superstring of the match in the primary text.

## STrans - Sentence Transformers

Sentence transformers are large language models (LLMs) optimised for sentence similarity. They are trained on BERT-like masked language models and similarly consist of a representation of vector embeddings, but unlike most other LLMs vectors represent sentences (in our case verses) and not word tokens. A particularly popular sentence transformer (and one that has been suggested to us by William Mattingly) is LaBSE. Our preliminary testing however suggests that for Old Church Slavonic uaritm/multilingual_en_uk_pl_ru seems to perform better.

We use the default accuracy function for transformer models, which is cosine similarity over the embedding vectors.

## BM25: Okapi Best Matching 25

The inclusion of this algorithm was inspired by William Mattingly and his [Latin Vulgate Verse Similarity Search](https://huggingface.co/spaces/medieval-data/latin-vulgate). This algorithm is based on [word frequencies](https://en.wikipedia.org/wiki/Okapi_BM25#The_ranking_function) disregarding word order. We lemmatize to improve indexing (whereas stemming seems to be expected). We normalise accuracy by dividing all accuracies by the largest one.

## Adding a new algorithm

To add a new algorithm, it needs to implement the logic of `app_*.py`. The find() method should provide a common set of parameters, wrapper() provides these and additional that could potentially be parametrised by gradio. interface() and __main__ are needed to run the gradio endpoint. To include the algorithm in the application, add it to the [list of available methods](https://github.com/mapto/bogoslov/blob/635e37f7eb61130441686706151fed30465510e2/src/main.py#L28). Finally, for advanced access, make sure to add the endpoint name of your model in the [web gateway](https://github.com/mapto/bogoslov/blob/635e37f7eb61130441686706151fed30465510e2/nginx.conf#L33), [exploratory interface](https://github.com/mapto/bogoslov/blob/635e37f7eb61130441686706151fed30465510e2/static/index.html#L101).

# Bibliography

Ruskov, Mikulka, Podtergera, Gavrilkov & Thompson (2025). Quotes at the Fingertips: The BogoSlov Project’s Combined Approach towards Identification of Biblical Material in Old Church Slavonic Texts. In Proceedings of the 21st Conference on Information and Research Science Connecting to Digital and Library Science. CEUR-WS. https://ceur-ws.org/Vol-3937/short8.pdf ([bibtex](static/references.bib))