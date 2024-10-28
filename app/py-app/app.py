import argparse
import logging.config
import logging.config
import os
import time
import uuid
import pathlib

from cltl.chatui.api import Chats
from cltl.chatui.memory import MemoryChats
from cltl.combot.event.emissor import Agent, ScenarioStarted, ScenarioStopped, TextSignalEvent
from cltl.combot.infra.config.k8config import K8LocalConfigurationContainer
from cltl.combot.infra.di_container import singleton
from cltl.combot.infra.event import Event
from cltl.combot.infra.event.memory import SynchronousEventBusContainer
from cltl.combot.infra.event_log import LogWriter
from cltl.combot.infra.resource.threaded import ThreadedResourceContainer
from cltl.combot.infra.time_util import timestamp_now
from cltl.emissordata.api import EmissorDataStorage
from cltl.emissordata.file_storage import EmissorDataFileStorage
from emissor.representation.scenario import Modality, Scenario, ScenarioContext
from emissor.representation.scenario import TextSignal

from cltl_service.chatui.service import ChatUiService
from cltl_service.combot.event_log.service import EventLogService

from cltl_service.emissordata.client import EmissorDataClient
from cltl_service.emissordata.service import EmissorDataService
from emissor.representation.util import serializer as emissor_serializer
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from emissor.representation.ldschema import emissor_dataclass

from myapp.template.api import DemoProcessor
from myapp.template.dummy_demo import HelloWorldProcessor
from myapp_service.template.service import DemoService

#### Added imports

from cltl.about.about import AboutImpl
from cltl.about.api import About
from cltl_service.about.service import AboutService
from cltl.brain.long_term_memory import LongTermMemory

from cltl.reply_generation.thought_selectors.random_selector import RandomSelector

from cltl.triple_extraction.api import DialogueAct
from cltl.triple_extraction.chat_analyzer import ChatAnalyzer
from cltl_service.brain.service import BrainService
from cltl_service.entity_linking.service import DisambiguationService
from cltl_service.reply_generation.service import ReplyGenerationService
from cltl_service.triple_extraction.service import TripleExtractionService

from cltl.dialogue_act_classification.api import DialogueActClassifier
from cltl.dialogue_act_classification.midas_classifier import MidasDialogTagger
from cltl.dialogue_act_classification.silicone_classifier import SiliconeDialogueActClassifier
from cltl_service.dialogue_act_classification.service import DialogueActClassificationService

from cltl.emotion_extraction.api import EmotionExtractor
from cltl.emotion_extraction.utterance_go_emotion_extractor import GoEmotionDetector
from cltl.emotion_extraction.utterance_vader_sentiment_extractor import VaderSentimentDetector
from cltl.emotion_responder.api import EmotionResponder
from cltl.emotion_responder.emotion_responder import EmotionResponderImpl
from cltl_service.emotion_extraction.service import EmotionExtractionService
from cltl_service.emotion_responder.service import EmotionResponderService

logging.config.fileConfig(os.environ.get('CLTL_LOGGING_CONFIG', default='config/logging.config'),
                          disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class InfraContainer(SynchronousEventBusContainer, K8LocalConfigurationContainer, ThreadedResourceContainer):
    pass


class EmissorStorageContainer(InfraContainer):
    @property
    @singleton
    def emissor_storage(self) -> EmissorDataStorage:
        return EmissorDataFileStorage.from_config(self.config_manager)

    @property
    @singleton
    def emissor_data_service(self) -> EmissorDataService:
        return EmissorDataService.from_config(self.emissor_storage,
                                              self.event_bus, self.resource_manager, self.config_manager)

    @property
    @singleton
    def emissor_data_client(self) -> EmissorDataClient:
        return EmissorDataClient("http://0.0.0.0:8000/emissor")

    def start(self):
        logger.info("Start Emissor Data Storage")
        super().start()
        self.emissor_data_service.start()

    def stop(self):
        try:
            logger.info("Stop Emissor Data Storage")
            self.emissor_data_service.stop()
        finally:
            super().stop()


class ChatUIContainer(InfraContainer):
    @property
    @singleton
    def chats(self) -> Chats:
        return MemoryChats()

    @property
    @singleton
    def chatui_service(self) -> ChatUiService:
        return ChatUiService.from_config(MemoryChats(), self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Chat UI")
        super().start()
        self.chatui_service.start()

    def stop(self):
        try:
            logger.info("Stop Chat UI")
            self.chatui_service.stop()
        finally:
            super().stop()


#### Added containers

class DialogueActClassficationContainer(InfraContainer):
    @property
    @singleton
    def dialogue_act_classifier(self) -> DialogueActClassifier:
        config = self.config_manager.get_config("cltl.dialogue_act_classification")
        implementation = config.get("implementation")

        if implementation == "midas":
            config = self.config_manager.get_config("cltl.dialogue_act_classification.midas")
            return MidasDialogTagger(config.get("model"))
        elif implementation == "silicone":
            return SiliconeDialogueActClassifier()
        elif not implementation:
            logger.warning("No DialogueClassifier implementation configured")
            return False
        else:
            raise ValueError("Unsupported DialogueClassifier implementation: " + implementation)

    @property
    @singleton
    def dialogue_act_classification_service(self) -> DialogueActClassificationService:
        if self.dialogue_act_classifier:
            return DialogueActClassificationService.from_config(self.dialogue_act_classifier,
                                                                self.event_bus, self.resource_manager,
                                                                self.config_manager)
        else:
            return False

    def start(self):
        super().start()
        if self.dialogue_act_classification_service:
            logger.info("Start Dialogue Act Classification Service")
            self.dialogue_act_classification_service.start()

    def stop(self):
        if self.dialogue_act_classification_service:
            logger.info("Stop Dialogue Act Classification Service")
            self.dialogue_act_classification_service.stop()
        super().stop()


class EmotionRecognitionContainer(InfraContainer):
    @property
    @singleton
    def emotion_extractor(self) -> EmotionExtractor:
        config = self.config_manager.get_config("cltl.emotion_recognition")
        implementation = config.get("impl")

        if implementation == "Go":
            config = self.config_manager.get_config("cltl.emotion_recognition.go")
            detector = GoEmotionDetector(config.get("model"))
        elif implementation == "Vader":
            detector = VaderSentimentDetector()
        elif not implementation:
            logger.warning("No EmotionExtractor implementation configured")
            detector = False
        else:
            raise ValueError("Unknown emotion extractor implementation: " + implementation)

        return detector

    @property
    @singleton
    def emotion_responder(self) -> EmotionResponder:
        return EmotionResponderImpl()

    @property
    @singleton
    def emotion_recognition_service(self) -> EmotionExtractionService:
        if self.emotion_extractor:
            return EmotionExtractionService.from_config(self.emotion_extractor, self.event_bus,
                                                        self.resource_manager, self.config_manager)
        else:
            return False

    @property
    @singleton
    def emotion_responder_service(self) -> EmotionResponderService:
        return EmotionResponderService.from_config(self.emotion_responder, self.event_bus,
                                                   self.resource_manager, self.config_manager)

    def start(self):
        super().start()
        if self.emotion_recognition_service:
            logger.info("Start Emotion Recognition service")
            self.emotion_recognition_service.start()

    def stop(self):
        try:
            if self.emotion_recognition_service:
                logger.info("Stop Emotion Recognition service")
                self.emotion_recognition_service.stop()
        finally:
            super().stop()



# class AboutAgentContainer(EmissorStorageContainer, InfraContainer):
#     @property
#     @singleton
#     def about_agent(self) -> About:
#         return AboutImpl()
#
#     @property
#     @singleton
#     def about_agent_service(self) -> GetToKnowYouService:
#         return AboutService.from_config(self.about_agent, self.emissor_data_client,
#                                         self.event_bus, self.resource_manager, self.config_manager)
#
#     def start(self):
#         logger.info("Start AboutAgent")
#         super().start()
#         self.about_agent_service.start()
#
#     def stop(self):
#         try:
#             logger.info("Stop AboutAgent")
#             self.about_agent_service.stop()
#         finally:
#             super().stop()

class TripleExtractionContainer(EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def triple_extraction_service(self) -> TripleExtractionService:
        config = self.config_manager.get_config("cltl.triple_extraction")
        implementation = config.get("implementation", multi=True)
        timeout = config.get_float("timeout") if "timeout" in config else 0.0

        analyzers = []
        if "CFGAnalyzer" in implementation:
            from cltl.triple_extraction.cfg_analyzer import CFGAnalyzer
            analyzers.append(CFGAnalyzer(process_questions=False))
        if "CFGQuestionAnalyzer" in implementation:
            from cltl.question_extraction.cfg_question_analyzer import CFGQuestionAnalyzer
            analyzers.append(CFGQuestionAnalyzer())
        if "StanzaQuestionAnalyzer" in implementation:
            from cltl.question_extraction.stanza_question_analyzer import StanzaQuestionAnalyzer
            analyzers.append(StanzaQuestionAnalyzer())
        if "OIEAnalyzer" in implementation:
            from cltl.triple_extraction.oie_analyzer import OIEAnalyzer
            analyzers.append(OIEAnalyzer())
        if "SpacyAnalyzer" in implementation:
            from cltl.triple_extraction.spacy_analyzer import spacyAnalyzer
            analyzers.append(spacyAnalyzer())
        if "ConversationalAnalyzer" in implementation:
            from cltl.triple_extraction.conversational_analyzer import ConversationalAnalyzer
            config = self.config_manager.get_config('cltl.triple_extraction.conversational')
            model_path = config.get('model_path')
            base_model = config.get('base_model')
            language = config.get("language")
            threshold = config.get_float("threshold")
            max_triples = config.get_int("max_triples")
            batch_size = config.get_int("batch_size")
            dialogue_acts = [DialogueAct.STATEMENT]
            analyzers.append(ConversationalAnalyzer(model_path=model_path, base_model=base_model, threshold=threshold,
                                                    max_triples=max_triples, batch_size=batch_size,
                                                    dialogue_acts=dialogue_acts, lang=language))

        if not analyzers:
            raise ValueError("No supported analyzers in " + implementation)

        logger.info("Using analyzers %s in Triple Extraction", implementation)

        return TripleExtractionService.from_config(ChatAnalyzer(analyzers, timeout=timeout), self.emissor_data_client,
                                                   self.event_bus,
                                                   self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Triple Extraction")
        super().start()
        self.triple_extraction_service.start()

    def stop(self):
        try:
            logger.info("Stop Triple Extraction")
            self.triple_extraction_service.stop()
        finally:
            super().stop()


class BrainContainer(InfraContainer):
    @property
    @singleton
    def brain(self) -> LongTermMemory:
        config = self.config_manager.get_config("cltl.brain")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")
        clear_brain = bool(config.get_boolean("clear_brain"))

        # TODO figure out how to put the brain RDF files in the EMISSOR scenario folder
        return LongTermMemory(address=brain_address,
                              log_dir=pathlib.Path(brain_log_dir),
                              clear_all=clear_brain)

    @property
    @singleton
    def brain_service(self) -> BrainService:
        return BrainService.from_config(self.brain, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Brain")
        super().start()
        self.brain_service.start()

    def stop(self):
        try:
            logger.info("Stop Brain")
            self.brain_service.stop()
        finally:
            super().stop()


class DisambiguationContainer(BrainContainer, InfraContainer):
    @property
    @singleton
    def disambiguation_service(self) -> DisambiguationService:
        config = self.config_manager.get_config("cltl.entity_linking")
        implementations = config.get("implementations")
        brain_address = config.get("address")
        brain_log_dir = config.get("log_dir")
        linkers = []

        if "NamedEntityLinker" in implementations:
            from cltl.entity_linking.linkers import NamedEntityLinker
            linker = NamedEntityLinker(address=brain_address,
                                       log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if "FaceIDLinker" in implementations:
            from cltl.entity_linking.face_linker import FaceIDLinker
            linker = FaceIDLinker(address=brain_address,
                                  log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if "PronounLinker" in implementations:
            # TODO This is OK here, we need to see how this will work in a containerized setting
            # from cltl.reply_generation.rl_replier import PronounLinker
            from cltl.entity_linking.linkers import PronounLinker
            linker = PronounLinker(address=brain_address,
                                   log_dir=pathlib.Path(brain_log_dir))
            linkers.append(linker)
        if not linkers:
            raise ValueError("Unsupported implementation " + implementations)

        logger.info("Initialized DisambiguationService with linkers %s",
                    [linker.__class__.__name__ for linker in linkers])

        return DisambiguationService.from_config(linkers, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Disambigution Service")
        super().start()
        self.disambiguation_service.start()

    def stop(self):
        try:
            logger.info("Stop Disambigution Service")
            self.disambiguation_service.stop()
        finally:
            super().stop()


class ReplierContainer(BrainContainer, EmissorStorageContainer, InfraContainer):
    @property
    @singleton
    def reply_service(self) -> ReplyGenerationService:
        config = self.config_manager.get_config("cltl.reply_generation")
        implementations = config.get("implementations")
        repliers = []

        if "LenkaReplier" in implementations:
            from cltl.reply_generation.lenka_replier import LenkaReplier
            thought_options = config.get("thought_options", multi=True) if "thought_options" in config else []
            paraphrase = config.get("paraphrase") if "paraphrase" in config else False
            model = config.get("model") if "model" in config else None
            instruct = config.get("instruct") if "instruct" in config else None
            temperature = config.get("temperature") if "temperature" in config else None
            max_tokens = config.get("max_tokens") if "max_tokens" in config else None
            randomness = float(config.get("randomness")) if "randomness" in config else 1.0
            replier = LenkaReplier(model=model, instruct=instruct, paraphrase=paraphrase, temperature=float(temperature), max_tokens=int(max_tokens), thought_selector=RandomSelector(randomness=randomness, priority=thought_options))
            repliers.append(replier)
        if "RLReplier" in implementations:
            from cltl.reply_generation.rl_replier import RLReplier
            # TODO This is OK here, we need to see how this will work in a containerized setting
            replier = RLReplier(self.brain)
            repliers.append(replier)
        if "LlamaReplier" in implementations:
            from cltl.reply_generation.llama_replier import LlamaReplier
            replier = LlamaReplier()
            repliers.append(replier)
        if "SimpleNLGReplier" in implementations:
            from cltl.reply_generation.simplenlg_replier import SimpleNLGReplier
            # TODO This is OK here, we need to see how this will work in a containerized setting
            replier = SimpleNLGReplier()
            repliers.append(replier)
        if not repliers:
            raise ValueError("Unsupported implementation " + implementations)

        return ReplyGenerationService.from_config(repliers, self.emissor_data_client, self.event_bus,
                                                  self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Repliers")
        super().start()
        self.reply_service.start()

    def stop(self):
        try:
            logger.info("Stop Repliers")
            self.reply_service.stop()
        finally:
            super().stop()


#
# class NLPContainer(InfraContainer):
#     @property
#     @singleton
#     def nlp(self) -> NLP:
#         config = self.config_manager.get_config("cltl.nlp.spacy")
#
#         return SpacyNLP(config.get('model'), config.get('entity_relations', multi=True))
#
#     @property
#     @singleton
#     def nlp_service(self) -> NLPService:
#         return NLPService.from_config(self.nlp, self.event_bus, self.resource_manager, self.config_manager)
#
#     def start(self):
#         logger.info("Start NLP service")
#         super().start()
#         self.nlp_service.start()
#
#     def stop(self):
#         try:
#             logger.info("Stop NLP service")
#             self.nlp_service.stop()
#         finally:
#             super().stop()

##### End of added containers


class DemoContainer(InfraContainer):
    @property
    @singleton
    def processor(self) -> DemoProcessor:
        return HelloWorldProcessor()

    @property
    @singleton
    def demo_service(self) -> DemoService:
        return DemoService.from_config(self.processor, self.event_bus, self.resource_manager, self.config_manager)

    def start(self):
        logger.info("Start Demo Service")
        super().start()
        self.demo_service.start()

    def stop(self):
        logger.info("Stop Demo Service")
        self.demo_service.stop()
        super().stop()


@emissor_dataclass
class ApplicationContext(ScenarioContext):
    speaker: Agent


class ApplicationContainer(ChatUIContainer,
                           TripleExtractionContainer,
                           DisambiguationContainer,
                           ReplierContainer,
                           BrainContainer,
                           #AboutAgentContainer,
                           EmotionRecognitionContainer, DialogueActClassficationContainer,
                           EmissorStorageContainer):
    def __init__(self, name: str):
        self._name = name

    @property
    @singleton
    def log_writer(self):
        config = self.config_manager.get_config("cltl.event_log")

        return LogWriter(config.get("log_dir"), serializer)

    @property
    @singleton
    def event_log_service(self):
        return EventLogService.from_config(self.log_writer, self.event_bus, self.config_manager)

    def _start_scenario(self):
        scenario_topic = self.config_manager.get_config("cltl.context").get("topic_scenario")
        scenario = self._create_scenario()
        self.event_bus.publish(scenario_topic,
                               Event.for_payload(ScenarioStarted.create(scenario)))
        self._scenario = scenario
        logger.info("Started scenario %s", scenario)

    def _stop_scenario(self):
        scenario_topic = self.config_manager.get_config("cltl.context").get("topic_scenario")
        self._scenario.ruler.end = timestamp_now()
        self.event_bus.publish(scenario_topic,
                               Event.for_payload(ScenarioStopped.create(self._scenario)))
        logger.info("Stopped scenario %s", self._scenario)

    def _create_scenario(self):
        signals = {
            Modality.TEXT.name.lower(): "./text.json",
        }

        scenario_start = timestamp_now()

        agent = Agent("Leolani", "http://cltl.nl/leolani/world/leolani")
        speaker = Agent(self._name, f"http://cltl.nl/leolani/world/{self._name.lower()}")
        scenario_context = ApplicationContext(agent, speaker)
        scenario = Scenario.new_instance(str(uuid.uuid4()), scenario_start, None, scenario_context, signals)
        utterance = f"Greetings %s, my name is %s and I am happy to talk to you" % (speaker.name, agent.name)
        signal = TextSignal.for_scenario(scenario, timestamp_now(), timestamp_now(), None, utterance)
        self.event_bus.publish("cltl.topic.text_out", Event.for_payload(TextSignalEvent.for_agent(signal)))
        return scenario

    def start(self):
        logger.info("Start EventLog")
        super().start()
        self.event_log_service.start()
        self._start_scenario()

    def stop(self):
        try:
            self._stop_scenario()
            time.sleep(1)
            logger.info("Stop EventLog")
            self.event_log_service.stop()
        finally:
            super().stop()


def serializer(obj):
    try:
        return emissor_serializer(obj)
    except Exception:
        try:
            return vars(obj)
        except Exception:
            return str(obj)


def main(name: str):
    ApplicationContainer.load_configuration()
    logger.info("Initialized Application")
    application = ApplicationContainer(name)
    with application as started_app:
        routes = {
            '/emissor': started_app.emissor_data_service.app,
            '/chatui': started_app.chatui_service.app,
        }

        web_app = DispatcherMiddleware(Flask("Text-eKG-Text app"), routes)

        run_simple('0.0.0.0', 8000, web_app, threaded=True, use_reloader=False, use_debugger=False, use_evalex=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Text-eKG-Text app')
    parser.add_argument('--name', type=str, required=False, help="Speaker name", default="Alice")
    args, _ = parser.parse_known_args()
    print ('ARG:', args.name)

    if not args.name.strip().isalpha():
        raise ValueError("The --name argument must contain only alphabet characters")
    print('PLEASE ENTER YOU NAME TO PROCEED!')
    name = input()
    main(name.strip())
    #main(args.name.strip())
