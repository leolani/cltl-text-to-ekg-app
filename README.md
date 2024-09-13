# Text to episodic Knowledge Graph
This is an example application that demonstrates how the Leolani event bus can be combined with an episodic Knowledge Graph (eKG). 
It represents an agent that takes a text signal from the event bus to do the following.

If the text is a statement:

1) extract triples, 
2) push triples to an external triple store that functions as the eKG, 
3) reason over the impact of the changes in the graph and return graph patterns as a response,
4) verbalise one of the graph patterns as the response.

If the text is a question:

1) extract the question,
2) Send the question as a SPARQL query to the eKG
3) Send the results back to the event bus as a response
4) verbalize the responss

The verbalised response is pushed back as a text signal to the event bus. 
The user input and the agent response as text signals are taken from and fed to the ChatUI application 
that runs in a browser on localhost (see below). Input and output can pushed iteratively through the ChatUI 
forming a conversation through which new triples are posted to the eKG continuously. 
The eKG will thus grow as the conversation proceeds. 
This agent requires that [GraphDB](https://graphdb.ontotext.com) is installed as a triple store and is running in parallel. 

This application is chat-only. It can be extended with speech and image processing components to make it multimodal.

## Check-out

To check out all code needed for the Leolani App, clone this repository including all submodules:

        git clone --recurse-submodules -j8 https://github.com/leolani/cltl-text-to-ekg-app.git

Checkout the current state of the parent

        git checkout --recurse-submodules

To pull the latest changes, you can run:

        git pull --recurse-submodules


After checkout of the main repository and the submodules, the repository content is as follows:

```
-rw-r--r--   1 staff  staff  2552 May 25 14:13 README.md
-rw-r--r--   1 staff  staff     9 May 25 14:13 VERSION
drwxr-xr-x  14 staff  staff   448 May 25 14:13 app
drwxr-xr-x   3 staff  staff    96 May 25 14:22 cltl-chat-ui
drwxr-xr-x   3 staff  staff    96 May 25 14:22 cltl-combot
drwxr-xr-x   3 staff  staff    96 May 25 14:22 cltl-emissor-data
drwxr-xr-x  17 staff  staff   544 May 25 17:41 cltl-knowledgeextraction
drwxr-xr-x  16 staff  staff   512 May 25 17:41 cltl-knowledgelinking
drwxr-xr-x  16 staff  staff   512 May 25 17:20 cltl-knowledgerepresentation
drwxr-xr-x  15 staff  staff   480 May 25 17:21 cltl-languagegeneration
drwxr-xr-x  14 staff  staff   448 May 25 14:13 cltl-requirements
drwxr-xr-x  27 staff  staff   864 May 25 17:12 emissor
-rw-r--r--   1 staff  staff   901 May 25 14:13 makefile
drwxr-xr-x   3 staff  staff    96 May 25 15:07 util
```
To build the agent, run the "make build" command (twice!) from the root and activate the virtual environment that is created.

## Run the agent

Checkout the repository as described in [Check-out](#check-out). Then go to the repository root, build the project,
activate the virtual environment for the Python application and run it. Altogether:

        git clone --recurse-submodules -j8 https://github.com/leolani/cltl-text-to-ekg-app.git
        cd cltl-text-to-ekg-app
        make build
        source venv/bin/activate
        cd py-app
        python app.py

The default name for you as a user is "Alice", the name of the agent is "Leolani". If you want to launch the system with a different name you can start it with:

        ```python app.py --name "your-name"```

You can then go to the chat interface [here](http://0.0.0.0:8000/chatui/static/chat.html) to type and see what the system responds.

NOTES:

* The "make build" may take 5 - 10 min
* If you use a knowledge Graph, remember to launch GraphDB and have a repository called 'sandbox'
* Remember to launch Docker before running
* Remember to use the virtual environment (created by the make buildcommand) located at cltl-text-to-ekg-app/venv

## Event bus integration

The event bus itself uses the following standard submodules:

* [cltl-chat-ui] the graphical user interface for having a chat dialogue
* [cltl-combot] shared code and representations
* [cltl-emissor-data] data elements for representing signals in EMISSOR
* [emissor] storing signals as sequence data in scenarios and temporal containers
* [cltl-requirements] for installing the dependencies
* [util] for creating make files to install submodules and dependencies in a virtual environment

The above submodules are necessary for any application that uses the event bus and EMISSOR.
For this agent, the following Github submodules are also needed in addition to the generic modules:

* [cltl-knowledgeextraction] for extracting triples from text
* [cltl-knowledgelinking] for linking triple subjects and objects to identities in the eKG
* [cltl-knowledgerepresentation] for integrating the triples into the eKG and obtaining a response
* [cltl-languagegeneration] for verbalising the response as text

The event bus pipeline for this application is as follows, 
where \<topics\> are the input/output of components represented as [component]:

```
<cltl.topic.text_in>
—> [knowledge extraction] —>  <cltl.topic.triple_extraction> 
—> [knowledge linking] —> <cltl.topic.knowledge>
—> [knowledge representation & knowledge reasoning] —> <cltl.topic.brain_response> 
—> [response selection and language generation] —> <cltl.topic.text_out>
```

The event bus pipeline dependencies are defined in the default.config file located in app/py-app/config 
together with various other settings specific to each submodule. Here we only show topic settings:

```
[cltl.triple_extraction]
topic_input : cltl.topic.text_in
topic_agent : cltl.topic.text_out
topic_output : cltl.topic.triple_extraction

[cltl.entity_linking]
topic_input : cltl.topic.triple_extraction
topic_output : cltl.topic.knowledge

[cltl.brain] ### used by cltl-knowledgerepresentation
topic_input : cltl.topic.knowledge
topic_output : cltl.topic.brain_response

[cltl.reply_generation]
topic_input : cltl.topic.brain_response
topic_output : cltl.topic.text_out

[cltl.chat-ui.events]
topic_utterance: cltl.topic.text_in
topic_response: cltl.topic.text_out
```

The topic_input and topic_output in the config file are used to direct output to a specific component 
only regardless of the modality of signal. In the above pipeline all the topics are of the modality Text Signal. 
Within each component the input and output topics are further processed according to the expected format.

For example, the [cltl-knowledge_extraction] component expects the utterance of an interlocutor as a Text Signal with the topic <cltl.topic.text_in>. 
It adds this to an internal representation of the dialogue. It processes the utterance given the dialogue history
and generates the triples. The result is a JSON structure that is given back to the event bus a Text Signal with the topic <cltl.topic.triple_extraction>, 
which is picked up by the next component which is [cltl-knowledgelinking]. 
The [cltl-knowledgelinking] tries to link text-based triples to what is already in the Knowledge Graph, resolving the IRIs based on the text reference or otherwise creating a new IRI. 
It modifies the triple representation accordingly and gives the output as a Text Signal back the event bus with the topic <cltl.topic.knowledge>.
This is picked up by the [cltl-knowledgerepresentation] to save the data in the Knowledge Graph. Any change or query to the Knowledge Graph results
in graph patterns that are given back to the event bus as a JSON Text Signal with the topic <cltl.topic.brain_response>. 
Finally, the [cltl-langaugegeneration] selects a response and verbalises this as <cltl.topic.text-out>.


## EMISSOR

The application collects interaction data in EMISSOR format as a sequence of signals. 
There is a scenario created in the folder *cltl-text-to-ekg/py-app/storage/emissor*
for each run of the application. This agent saves the following data to disk for each scenario:

1. the scenario meta information in a json file with the same name as the scenario folder
2. the user input as <text signal> and system response as <text signal> in text.json.
3. files in a subfolder named "rdf" with the triples that have been added to the Knowledge Graph in RDF-trig format

See the documentation for EMISSOR for more details.
## Details about the components

### Triple extraction
There are various triple extraction modules that can be used:

1) Context Free Grammer: rules and lexicon specifically designed for extracting triples from simple statement in the social domain (English only)
2) Stanford Open IE: triple extraction trained from Wikipedia text (English only)
3) Conversational triple extraction: trained from conversationsal data to extract triples from sequences of turns (user, agent, user) dealing with conversational phenomena such as coreference, ellipsis, negation, questions (English only)
4) Same as 3) but using a multilingual Bert model, which works for 100 languages

These modules can be selected in the configuration file before launching the agent, along with various other settings, as shown below in which two triple extraction modules will run simultaneously:

```
[cltl.triple_extraction]
implementation: CFGAnalyzer, ConversationalAnalyzer
timeout: 15
topic_input : cltl.topic.text_in
topic_agent : cltl.topic.text_out
topic_output : cltl.topic.triple_extraction
topic_scenario : cltl.topic.scenario
```


```
[cltl.triple_extraction.conversational]
model_path: resources/conversational_triples
base_model: google-bert/bert-base-multilingual-cased
#base_model: albert-base-v2
language: en
threshold: 0.7
max_triples: 64
batch_size: 4
```

The modules extract triples as a list of three elements: the subject, predicate and object. 
A triple are included in so-called JSON capsules that also contains the meta information on the context, conversation and turn through identifiers, 
the actual text representing the turn, the source or author of the utterance, the perspective of the source (speaker) on the triple and optionally other information from the context. 
Below is an example of such a capsule extracted for the utterance "I have a house":

```
{'chat': '8d542339-c11b-4b9c-8a2b-257c1aa77562', 
'turn': '8ab2728a-915f-40f5-b2ad-7579f113c787', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'I have a house', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-14', 
'subject': {'label': 'human', 'type': [], 'uri': None}, 
'predicate': {'label': 'have', 'type': [], 'uri': None}, 
'object': {'label': 'a-house', 'type': [], 'uri': None}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': '8d542339-c11b-4b9c-8a2b-257c1aa77562', 
'timestamp': 1717655170734}
```

```commandline
06/20/24 14:54:58 DEBUG    cltl_service.brain.service                                   
Capsule: ({'chat': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 
'turn': 'c4428b6e-b8d2-4bbf-986a-2d1d05b0dcb1', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'John likes music', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-16', 
'subject': {'label': 'john', 'type': [], 'uri': 'http://cltl.nl/leolani/world/john'}, 
'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 
'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'timestamp': 1718888097825})
```

In this example, the human interlocutor is anonymous and identified as "Human". 

```commandline
06/20/24 14:55:27 DEBUG    cltl_service.brain.service                                   
Processed UtteranceType.STATEMENT (
{'response': '204', 'statement': {'chat': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'turn': 'c4428b6e-b8d2-4bbf-986a-2d1d05b0dcb1', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'John likes music', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-16', 'subject': {'label': 'john', 'type': ['john'], 'uri': 'http://cltl.nl/leolani/world/john'}, 'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 'object': {'label': 'music', 'type': ['music'], 'uri': 'http://cltl.nl/leolani/world/music'}, 'perspective': <cltl.brain.infrastructure.api.Perspective object at 0x12a55a280>, 'context_id': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'timestamp': 1718888097825, 'triple': john_like_music [john_->_music])}, 'thoughts': {'statement_novelty': [], 'entity_novelty': new subject - new object, 'negation_conflicts': [], 'complement_conflict': [], 'subject_gaps': 96 gaps as subject: e.g. john be-from location - 44 gaps as object: e.g. john know agent, 'complement_gaps': 95 gaps as subject: e.g. music be-parent-of agent - 43 gaps as object: e.g. music be-grandfather-of agent, 'overlaps': 0 subject overlaps: e.g. '' - 0 object overlaps: e.g. ''}, 'rdf_log_path': PosixPath('storage/rdf/2024-06-20-14-53/brain_log_2024-06-20-14-55-24-455739')})

```

```commandline
Leolani> If you don't mind me asking. Has john been spouse of person?
```
The triple extraction not only processes the input utterances of the user but also 
```commandline
06/20/24 14:57:51 DEBUG    cltl_service.brain.service                                   Processed UtteranceType.QUESTION ({'response': [{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/john'}, 'slabel': {'type': 'literal', 'value': 'john'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}], 'question': {'chat': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'turn': '022094c8-8905-422f-90d7-302df076d1c5', 'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 'utterance': 'Who likes music?', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-16', 'subject': {'label': '', 'type': [], 'uri': None}, 'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 'context_id': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'timestamp': 1718888271633, 'triple': ?_like_music [_->_])}, 'rdf_log_path': None})
06/20/24 14:57:51 DEBUG    cltl_service.brain.service                                   Capsule: ({'chat': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'turn': '022094c8-8905-422f-90d7-302df076d1c5', 'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 'utterance': 'Who likes music?', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-16', 'subject': {'label': '', 'type': [], 'uri': None}, 'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 'context_id': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'timestamp': 1718888271633})
06/20/24 14:57:51 WARNING  cltl.brain.RdfBuilder                                        Unknown type: music
06/20/24 14:57:51 INFO     cltl.brain.LongTermMemory                                    Triple in question: ?_like_music [_->_])

```
```commandline
{'chat': 'b34e27aa-d916-4681-9a55-bd25f5478805', 
'turn': '0598c96e-5e64-4c4a-a317-8660f387d747', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'who likes music?', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-16', 
'subject': {'label': '', 'type': [], 'uri': None}, 
'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 
'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': 'b34e27aa-d916-4681-9a55-bd25f5478805', 
'timestamp': 1717753894674, 'triple': ?_like_music [_->_])})
```

```commandline
06/20/24 14:57:51 DEBUG    cltl_service.brain.service                                   
Processed UtteranceType.QUESTION ({'response': [
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/john'}, 'slabel': {'type': 'literal', 'value': 'john'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}], 
'question': {'chat': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'turn': '022094c8-8905-422f-90d7-302df076d1c5', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'Who likes music?', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-16', 
'subject': {'label': '', 'type': [], 'uri': None}, 
'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 
'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': 'f51d2acf-a7df-4156-90e4-1c00ee0ffbd5', 'timestamp': 1718888271633, 
'triple': ?_like_music [_->_])}, 'rdf_log_path': None})
```

```commandline
Leolani> I have heard this before. I have heard about music before
```
```commandline
({'response': [{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/leolani'}, 
'slabel': {'type': 'literal', 'value': 'leolani'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 
'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': 'human'}, 
'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 
'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 
'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 
'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}, 
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/piek'}, 
'slabel': {'type': 'literal', 'value': 'piek'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 
'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': ''}}, 
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/'}, 'slabel': {'type': 'literal', 'value': 'None'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}, {'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/human'}, 'slabel': {'type': 'literal', 'value': 'human'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': ''}}, {'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/i'}, 'slabel': {'type': 'literal', 'value': 'i'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}, {'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/thomas'}, 'slabel': {'type': 'literal', 'value': 'thomas'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': ''}}, {'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/who'}, 'slabel': {'type': 'literal', 'value': 'who'}, 'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}], 'question': {'chat': 'b34e27aa-d916-4681-9a55-bd25f5478805', 'turn': '0598c96e-5e64-4c4a-a317-8660f387d747', 'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 'utterance': 'who likes music?', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-16', 'subject': {'label': '', 'type': [], 'uri': None}, 'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 'context_id': 'b34e27aa-d916-4681-9a55-bd25f5478805', 'timestamp': 1717753894675, 'triple': ?_like_music [_->_])}, 'rdf_log_path': None})

```

```commandline
Capsule: ({'chat': '5d75a43e-12ff-4859-9857-8abf02369468', 
'turn': '1f149469-7cf0-4a24-9b85-46a88e74281e', 
'author': {'label': 'Human', 'type': ['person'], 
'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'John likes music', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-16', 
'subject': {'label': 'that', 'type': [], 'uri': 'http://cltl.nl/leolani/world/that'}, 
'predicate': {'label': 'hear', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/hear'}, 
'object': {'label': 'leolani', 'type': ['robot'], 'uri': 'http://cltl.nl/leolani/world/leolani'}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': '5d75a43e-12ff-4859-9857-8abf02369468', 'timestamp': 1718886740179})

```
### Knowledge response

The JSON capsule is pushed as an output topic to the event bus, where it is picked up by the knowledge-representation module that integrates it in the eKG. Next it calls the reasoner module to analyse the impact of the integration. 
There are two types of user input and two types of responses:

* user makes a statement, agent responds with a question or a statement
* user asks a question, agents responds with an answer (including a response in case there is no answer)


```commandline
Processed UtteranceType.STATEMENT 
({'response': '204', 
'statement': {'chat': '5d75a43e-12ff-4859-9857-8abf02369468', 
'turn': '1f149469-7cf0-4a24-9b85-46a88e74281e', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'John likes music', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-16', 'subject': {'label': 'that', 'type': ['food'], 'uri': 'http://cltl.nl/leolani/world/that'}, 'predicate': {'label': 'hear', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/hear'}, 'object': {'label': 'leolani', 'type': ['robot'], 'uri': 'http://cltl.nl/leolani/world/leolani'}, 'perspective': <cltl.brain.infrastructure.api.Perspective object at 0x1324f8b50>, 'context_id': '5d75a43e-12ff-4859-9857-8abf02369468', 'timestamp': 1718886740179, 'triple': that_hear_leolani [food_->_robot])}, 'thoughts': {'statement_novelty': [], 'entity_novelty': new subject - existing object, 'negation_conflicts': [], 'complement_conflict': [], 'subject_gaps': 0 gaps as subject: e.g. '' - 0 gaps as object: e.g. '', 'complement_gaps': 100 gaps as subject: e.g. leolani be-partner-of person - 71 gaps as object: e.g. leolani be-husband-of agent, 'overlaps': 0 subject overlaps: e.g. '' - 0 object overlaps: e.g. ''}, 'rdf_log_path': PosixPath('storage/rdf/2024-06-20-14-24/brain_log_2024-06-20-14-32-25-566253')})

```
```
({'response': '204', 'statement': 
{'chat': '5d75a43e-12ff-4859-9857-8abf02369468', 'turn': '4d4be41d-1f43-416a-8132-ba3bbf925978', 
'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'I have a house', 'utterance_type': <UtteranceType.STATEMENT: '1'>, 'position': '0-14', 
'subject': {'label': 'human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'predicate': {'label': 'have', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/have'}, 
'object': {'label': 'a-house', 'type': ['🐕'], 'uri': 'http://cltl.nl/leolani/world/a-house'}, 
'perspective': <cltl.brain.infrastructure.api.Perspective object at 0x132584a30>, 
'context_id': '5d75a43e-12ff-4859-9857-8abf02369468', 'timestamp': 1718886330994, 
'triple': human_have_a-house [human_->_🐕])}, 
'thoughts': {'statement_novelty': [], 
'entity_novelty': existing subject - existing object, 
'negation_conflicts': [], 
'complement_conflict': [], 
'subject_gaps': 100 gaps as subject: e.g. leolani read book - 71 gaps as object: e.g. leolani be-grandmother-of agent, 
'complement_gaps': 5 gaps as subject: e.g. a-house be-inside container - 29 gaps as object: e.g. a-house write person, 
'overlaps': 0 subject overlaps: e.g. '' - 0 object overlaps: e.g. ''}, 
'rdf_log_path': PosixPath('storage/rdf/2024-06-20-14-24/brain_log_2024-06-20-14-25-31-252186')})
```

```commandline
"That rings a bell. I have heard about a house before"
```
The next response shows an answer of the agent to a question of the user

```
brain_response[response]) 
{'response': [
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/piek'}, 'slabel': {'type': 'literal', 'value': 'piek'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': ''}}, 
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/'}, 'slabel': {'type': 'literal', 'value': 'None'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': 'human'}, 'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}, 
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/human'}, 'slabel': {'type': 'literal', 'value': 'human'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': ''}}, 
{'s': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/i'}, 'slabel': {'type': 'literal', 'value': 'i'}, 
'p': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 'pOriginal': {'type': 'uri', 'value': 'http://cltl.nl/leolani/n2mu/like'}, 
'o': {'type': 'uri', 'value': 'http://cltl.nl/leolani/world/music'}, 'olabel': {'type': 'literal', 'value': 'music'}, 
'authorlabel': {'type': 'literal', 'value': 'human'}, 
'certaintyValue': {'type': 'literal', 'value': 'CERTAIN'}, 
'polarityValue': {'type': 'literal', 'value': 'POSITIVE'}, 
'sentimentValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}, 
'emotionValue': {'type': 'literal', 'value': 'UNDERSPECIFIED'}}], 
'question': {'chat': '44b0b157-2cce-45f4-b4e7-cc61df19b777', 'turn': '14179620-0b9b-4890-b94e-9938e4d397dd', 'author': {'label': 'Human', 'type': ['person'], 'uri': 'http://cltl.nl/leolani/world/human'}, 
'utterance': 'who likes music', 'utterance_type': <UtteranceType.QUESTION: '2'>, 'position': '0-15', 
'subject': {'label': '', 'type': [], 'uri': None}, 
'predicate': {'label': 'like', 'type': [], 'uri': 'http://cltl.nl/leolani/n2mu/like'}, 
'object': {'label': 'music', 'type': [], 'uri': 'http://cltl.nl/leolani/world/music'}, 
'perspective': {'sentiment': 0.0, 'certainty': 1.0, 'polarity': 1.0, 'emotion': 0.0}, 
'context_id': '44b0b157-2cce-45f4-b4e7-cc61df19b777', 'timestamp': 1717667799167, 
'triple': ?_like_music [_->_])}, 'rdf_log_path': None}
```
LenkaReplier
someone told me piek like music and that you like music and that thomas like music and you told me I like music and that human like music and that i like music and that who like music
