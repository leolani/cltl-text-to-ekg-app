SHELL = /bin/bash

project_dependencies ?= $(addprefix $(project_root)/, \
		emissor \
		cltl-combot \
		cltl-requirements \
		cltl-emissor-data \
		cltl-chat-ui \
        cltl-knowledgeextraction \
        cltl-knowledgelinking \
        cltl-knowledgerepresentation \
        cltl-languagegeneration \
		app)

git_remote ?= https://github.com/leolani

include util/make/makefile.base.mk
include util/make/makefile.component.mk
include util/make/makefile.py.base.mk
include util/make/makefile.git.mk

sources =

spacy.lock: venv
	test -e spacy.lock || (source venv/bin/activate; python -m spacy download en)
	test -e spacy.lock || (source venv/bin/activate; python -m spacy download nl)
	touch spacy.lock


nltk.lock: venv
	test -e nltk.lock || (source venv/bin/activate; python -m nltk.downloader -d ~/nltk_data all)
	touch nltk.lock

py-app/resources/conversational_triples/models.lock:
	mkdir -p py-app/resources/conversational_triples
	wget "https://vu.data.surfsara.nl/index.php/s/Ib6OcZHpfUyB5fm" -O py-app/resources/conversational_triples/argument_extraction_bert-base-multilingual-cased.pt
	wget "https://vu.data.surfsara.nl/index.php/s/LKTkoSZZpflaIaw" -O py-app/resources/conversational_triples/candidate_scorer_bert-base-multilingual-cased.pt
	wget "https://vu.data.surfsara.nl/index.php/s/WpL1vFChlQpkbqW/download" -O py-app/resources/conversational_triples/models.zip
	unzip -j -d py-app/resources/conversational_triples py-app/resources/conversational_triples/models.zip
	rm py-app/resources/conversational_triples/models.zip
	touch py-app/resources/conversational_triples/models.lock


.PHONY: build
build: venv \
	nltk.lock spacy.lock \
	py-app/resources/conversational_triples/models.lock


.PHONY: clean
clean: py-clean base-clean
	rm -f spacy.lock nltk.lock
	rm -rf py-app/resources/conversational_triples