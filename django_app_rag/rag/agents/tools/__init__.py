from pathlib import Path
from typing import Any

from django_app_rag.rag.logging_setup import get_logger

logger = get_logger(__name__)
from smolagents import LiteLLMModel, MessageRole, MultiStepAgent, ToolCallingAgent

from django_app_rag.rag.settings import settings

from .summarizer import HuggingFaceEndpointSummarizerTool, OpenAISummarizerTool
from .what_can_i_do import what_can_i_do
from django_app_rag.rag.monitoring.mlflow import mlflow_track
from .diskstorage_retriever import DiskStorageRetrieverTool
from .question_answer import QuestionAnswerTool

def get_agent(retriever_config_path: Path) -> "AgentWrapper":
    agent = AgentWrapper.build_from_smolagents(
        retriever_config_path=retriever_config_path
    )

    return agent


class AgentWrapper:
    def __init__(self, agent: MultiStepAgent) -> None:
        self.__agent = agent

    @property
    def input_messages(self) -> list[dict]:
        return self.__agent.input_messages

    @property
    def agent_name(self) -> str:
        return self.__agent.agent_name

    @property
    def max_steps(self) -> str:
        return self.__agent.max_steps

    @classmethod
    def build_from_smolagents(cls, retriever_config_path: Path) -> "AgentWrapper":
        retriever_tool = DiskStorageRetrieverTool(config_path=retriever_config_path)
        question_answer_tool = QuestionAnswerTool()
        
        if settings.USE_HUGGINGFACE_DEDICATED_ENDPOINT:
            logger.warning(
                f"Using Hugging Face dedicated endpoint as the summarizer with URL: {settings.HUGGINGFACE_DEDICATED_ENDPOINT}"
            )
            summarizer_tool = HuggingFaceEndpointSummarizerTool()
        else:
            logger.warning(
                f"Using OpenAI as the summarizer with model: {settings.OPENAI_MODEL_ID}"
            )
            summarizer_tool = OpenAISummarizerTool(stream=False)

        model = LiteLLMModel(
            model_id=settings.OPENAI_MODEL_ID,
            api_base="https://api.openai.com/v1",
            api_key=settings.OPENAI_API_KEY,
        )

        agent = ToolCallingAgent(
            tools=[what_can_i_do, retriever_tool, question_answer_tool, summarizer_tool],
            model=model,
            max_steps=3,
            verbosity_level=2,
            return_full_result=True,
        )

        return cls(agent)

    @mlflow_track(name="Agent.run")
    def run(self, task: str, **kwargs) -> Any:
        full_result = self.__agent.run(task, **kwargs)
        result = full_result.output

        model = self.__agent.model
        metadata = {
            # "system_prompt": self.__agent.system_prompt,
            # "system_prompt_template": self.__agent.system_prompt_template,
            # "tool_description_template": self.__agent.tool_description_template,
            "tools": self.__agent.tools,
            "model_id": self.__agent.model.model_id,
            "api_base": self.__agent.model.api_base,
        }
        
        # Add token counts if available
        if hasattr(model, 'last_input_token_count'):
            metadata["input_token_count"] = model.last_input_token_count
        if hasattr(model, 'last_output_token_count'):
            metadata["output_token_count"] = model.last_output_token_count
        if hasattr(self.__agent, "step_number"):
            metadata["step_number"] = self.__agent.step_number
        import mlflow
        mlflow.set_tags({"agent": True})
        mlflow.log_dict(metadata, "trace.json")

        # Try to extract JSON output from QuestionAnswerTool from memory steps
        json_output = self._extract_question_answer_json_from_steps()
        if json_output:
            return json_output

        return result

    def _extract_question_answer_json_from_steps(self) -> Any:
        """
        Extract JSON output from QuestionAnswerTool from agent memory steps.
        """
        import json
        
        try:
            print("🔍 Trying to extract QuestionAnswerTool response from memory steps...")
            
            # Look through all memory steps for QuestionAnswerTool observations
            for step in self.__agent.memory.steps:
                if hasattr(step, 'tool_calls') and step.tool_calls:
                    for tool_call in step.tool_calls:
                        if tool_call.name == "question_answer_tool":
                            print(f"🔍 Found QuestionAnswerTool call in step")
                            # The observation should be in the step's observations
                            if hasattr(step, 'observations') and step.observations:
                                print(f"🔍 Step observations: {step.observations[:200]}...")
                                
                                # Try to extract JSON from the observations
                                json_output = step.observations
                                if json_output:
                                    logger.info("Found QuestionAnswerTool JSON output from memory steps")
                                    return json_output
                                else:
                                    print("❌ No valid JSON found in step observations")
            
            print("❌ No QuestionAnswerTool found in memory steps")
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting JSON from memory steps: {e}")
            print(f"🔴 Error in _extract_question_answer_json_from_steps: {e}")
            return None

