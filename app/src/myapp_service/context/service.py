import logging
import uuid
from typing import Optional

from cltl.combot.event.emissor import ScenarioStopped
from cltl.combot.event.emissor import TextSignalEvent, Agent, ScenarioStarted, ScenarioEvent
from cltl.combot.infra.config import ConfigurationManager
from cltl.combot.infra.event import Event, EventBus
from cltl.combot.infra.resource import ResourceManager
from cltl.combot.infra.time_util import timestamp_now
from cltl.combot.infra.topic_worker import TopicWorker
from emissor.representation.ldschema import emissor_dataclass
from emissor.representation.scenario import TextSignal, Modality, ScenarioContext, Scenario

logger = logging.getLogger(__name__)


@emissor_dataclass
class ApplicationContext(ScenarioContext):
    speaker: Optional[Agent]


class ContextService:
    @classmethod
    def from_config(cls, event_bus: EventBus, resource_manager: ResourceManager, config_manager: ConfigurationManager):
        config = config_manager.get_config("app.context")

        scenario_topic = config.get("topic_scenario")
        text_in_topic = config.get("topic_text_in")
        text_forward_topic = config.get("topic_text_forward")
        text_out_topic = config.get("topic_text_out")

        return cls(scenario_topic, text_in_topic, text_forward_topic, text_out_topic,
                   event_bus, resource_manager)

    def __init__(self, scenario_topic: str, input_topic: str, forward_topic: str, output_topic: str,
                 event_bus: EventBus, resource_manager: ResourceManager):
        self._event_bus = event_bus
        self._resource_manager = resource_manager

        self._scenario_topic = scenario_topic
        self._input_topic = input_topic
        self._forward_topic = forward_topic
        self._output_topic = output_topic

        self._topic_worker = None
        self._scenario = None
        self._name = None

    def start(self, timeout=30):
        topics = [self._scenario_topic, self._input_topic]
        self._topic_worker = TopicWorker(topics, self._event_bus, provides=[self._output_topic],
                                         resource_manager=self._resource_manager, processor=self._process,
                                         name=self.__class__.__name__)
        self._topic_worker.start().wait()

    def stop(self):
        if not self._topic_worker:
            pass

        self._topic_worker.stop()
        self._topic_worker.await_stop()
        self._topic_worker = None

    @property
    def app(self):
        """
        Flask endpoint for REST interface.
        """
        return None

    def _process(self, event: Event):
        logger.debug("Received event on topic %s", event.metadata.topic)

        if event.metadata.topic == self._scenario_topic:
            if event.payload.type == ScenarioStopped.__name__:
                if not self._scenario:
                    self.start_scenario()
                elif event.payload.scenario.id == self._scenario.id:
                    logger.info("Cleared scenario %s", self._scenario.id)
                    self._scenario = None
                    self._name = None
            elif event.payload.type == ScenarioStarted.__name__:
                utterance = f"Hi, my name is {self._scenario.context.agent.name} and I am happy to talk to you! What is your name?"
                signal = TextSignal.for_scenario(self._scenario.id, timestamp_now(), timestamp_now(), None, utterance)
                self._event_bus.publish(self._output_topic, Event.for_payload(TextSignalEvent.for_agent(signal)))
                logger.info("Requested speaker name for scenario %s", event.payload.scenario.id)
        elif event.metadata.topic == self._input_topic:
            if self._scenario and self._name and (event.payload.signal.text.lower() == "goodbye" or event.payload.signal.text.lower() == "bye"):
                logger.debug("Received stop word for scenario %s", self._scenario.id)

                signal = TextSignal.for_scenario(self._scenario.id, timestamp_now(), timestamp_now(), None, "Goodbye!")
                self._event_bus.publish(self._output_topic, Event.for_payload(TextSignalEvent.for_agent(signal)))

                self.stop_scenario()
            elif self._scenario and self._name:
                logger.debug("Forwarded text signal %s", event.payload.signal.text)
                signal = TextSignal.for_scenario(self._scenario.id, timestamp_now(), timestamp_now(), None, event.payload.signal.text)
                self._event_bus.publish(self._forward_topic, Event.for_payload(TextSignalEvent.for_agent(signal)))
                #self._event_bus.publish(self._forward_topic, Event.for_payload(event.payload))
            elif self._scenario and not self._name:
                self._name = event.payload.signal.text
                self._update_scenario_speaker(self._name)

                signal = TextSignal.for_scenario(self._scenario.id, timestamp_now(), timestamp_now(), None, f"Hi {self._name}!")
                self._event_bus.publish(self._output_topic, Event.for_payload(TextSignalEvent.for_agent(signal)))
            elif not self._scenario:
                logger.debug("Received text signal outside scenario: %s", event.payload.signal.text)
                self.start_scenario()

    def _create_payload(self, response):
        signal = TextSignal.for_scenario(self._scenario.id, timestamp_now(), timestamp_now(), None, response)

        return TextSignalEvent.create(signal)

    def start_scenario(self):
        if self._scenario:
            raise ValueError("Scenario already started")

        scenario_topic = self._scenario_topic
        self._scenario = self._create_scenario()
        self._event_bus.publish(scenario_topic, Event.for_payload(ScenarioStarted.create(self._scenario)))

        logger.info("Started scenario %s", self._scenario)

    def stop_scenario(self):
        if not self._scenario:
            raise ValueError("No active scenario")

        scenario_topic = self._scenario_topic
        self._scenario.ruler.end = timestamp_now()
        self._event_bus.publish(scenario_topic, Event.for_payload(ScenarioStopped.create(self._scenario)))

        logger.info("Stopped scenario %s", self._scenario.id)

        self._scenario = None
        self._name = None

    def _update_scenario_speaker(self, name):
        self._scenario.context.speaker = Agent(name, f"http://cltl.nl/leolani/world/{name.lower()}")
        self._event_bus.publish(self._scenario_topic, Event.for_payload(ScenarioEvent.create(self._scenario)))

        logger.info("Human speaker is set to %s, updated scenario %s", self._name, self._scenario)

    def _create_scenario(self):
        signals = {
            Modality.TEXT.name.lower(): "./text.json",
        }

        scenario_start = timestamp_now()
        agent = "http://cltl.nl/leolani/world/leolani"
        scenario_context = ApplicationContext(agent, None)

        return Scenario.new_instance(str(uuid.uuid4()), scenario_start, None, scenario_context, signals)
