import json
import os
from typing import Dict, Any, Optional, cast
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from models.evaluation import EvaluationResult, RubricDimensions
from config import Config


class LLMService:

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        
        if not self.api_key:
            import sys
            print("[LLM_SERVICE] API key check failed:", file=sys.stderr)
            print(f"  Config.OPENAI_API_KEY: {Config.OPENAI_API_KEY}", file=sys.stderr)
            print(f"  api_key param: {api_key}", file=sys.stderr)
            raise ValueError("OpenAI API key is required")
        
        self.api_key = self.api_key.strip().strip('"').strip("'")
        
        if not self.api_key.startswith('sk-'):
            import sys
            print(f"[LLM_SERVICE] Invalid API key format: {self.api_key[:20]}", file=sys.stderr)
            raise ValueError("Invalid OpenAI API key format (must start with 'sk-')")

        self.client = OpenAI(api_key=self.api_key)
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts"
        )

        self.remediation_prompt = self._load_prompt("remediation_prompt.txt")
        self.mini_lesson_prompt = self._load_prompt("mini_lesson_prompt.txt")
        self.evaluation_prompt = self._load_prompt("evaluation_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        prompt_path = os.path.join(self.prompts_dir, filename)
        try:
            with open(prompt_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    def _call_llm(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a training engine for difficult conversations. "
                            "Always respond with valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            return response.choices[0].message.content or ""

        except RateLimitError as e:
            raise Exception(f"OpenAI rate limit exceeded: {str(e)}")
        except APIConnectionError as e:
            raise Exception(f"OpenAI API connection error: {str(e)}")
        except APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error calling LLM: {str(e)}")

    def generate_remediation(
        self, topic: str, user_answer: str, failure_reason: str, failure_count: int
    ) -> Dict[str, Any]:
        prompt = self.remediation_prompt.format(
            topic=topic,
            failure_count=failure_count,
            user_answer=user_answer,
            failure_reason=failure_reason,
        )

        response_text = self._call_llm(prompt, temperature=0.7, max_tokens=1500)

        try:
            result = cast(Dict[str, Any], json.loads(response_text))

            required_keys = [
                "explanation",
                "remedial_scenario",
                "remedial_options",
                "remedial_correct_answer",
                "hint",
            ]

            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key in LLM response: {key}")

            if (
                not isinstance(result["remedial_options"], list)
                or len(result["remedial_options"]) != 4
            ):
                raise ValueError("remedial_options must be a list of 4 options")

            if result["remedial_correct_answer"] not in ["A", "B", "C", "D"]:
                raise ValueError("remedial_correct_answer must be A, B, C, or D")

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")

    def generate_mini_lesson(self, topic: str) -> Dict[str, Any]:
        prompt = self.mini_lesson_prompt.format(topic=topic)

        response_text = self._call_llm(prompt, temperature=0.7, max_tokens=2000)

        try:
            result = cast(Dict[str, Any], json.loads(response_text))

            required_keys = [
                "lesson_title",
                "core_principle",
                "examples",
                "common_mistakes",
                "key_takeaway",
            ]

            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key in LLM response: {key}")

            if not isinstance(result["examples"], list) or len(result["examples"]) == 0:
                raise ValueError("examples must be a non-empty list")

            for example in result["examples"]:
                required_example_keys = [
                    "situation",
                    "wrong_approach",
                    "right_approach",
                    "why_it_works",
                ]
                for key in required_example_keys:
                    if key not in example:
                        raise ValueError(f"Missing required key in example: {key}")

            if not isinstance(result["common_mistakes"], list):
                raise ValueError("common_mistakes must be a list")

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")

    def evaluate_free_form(
        self, user_answer: str, scenario: str, gold_response: str, step_id: int
    ) -> EvaluationResult:
        prompt = self.evaluation_prompt.format(
            step_id=step_id,
            scenario=scenario,
            user_answer=user_answer,
            gold_response=gold_response,
        )

        response_text = self._call_llm(prompt, temperature=0.3, max_tokens=1500)

        try:
            result = cast(Dict[str, Any], json.loads(response_text))

            dimensions_data = result.get("dimensions", {})
            dimensions = RubricDimensions(
                de_escalation=float(dimensions_data.get("de_escalation", 0)),
                validation=float(dimensions_data.get("validation", 0)),
                clarity=float(dimensions_data.get("clarity", 0)),
                autonomy=float(dimensions_data.get("autonomy", 0)),
                next_step=float(dimensions_data.get("next_step", 0)),
            )

            total_score = dimensions.total_score()

            feedback_parts = [result.get("feedback", "")]

            if "strengths" in result and result["strengths"]:
                feedback_parts.append(
                    "\n\nStrengths:\n- " + "\n- ".join(result["strengths"])
                )

            if "improvements" in result and result["improvements"]:
                feedback_parts.append(
                    "\n\nAreas for improvement:\n- "
                    + "\n- ".join(result["improvements"])
                )

            feedback = "".join(feedback_parts)

            evaluation_result = EvaluationResult(
                passed=total_score >= 7.0,
                score=total_score,
                feedback=feedback,
                dimensions=dimensions,
                threshold=7.0,
            )

            return evaluation_result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to create EvaluationResult: {str(e)}")
