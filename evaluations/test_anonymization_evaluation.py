#!/usr/bin/env python3
"""
Automatic evaluation system for PromptSan anonymization
Tests multiple LLM models on datasets with precise scoring
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Import PromptSan
sys.path.insert(0, ".")
from promptsan.config import SanConfig
from promptsan.sanitizer import PromptSanitizer


@dataclass
class TestResult:
    """Result of an anonymization test"""

    test_id: str
    model_name: str
    success: bool
    found_entities: Dict[str, str]
    expected_entities: Dict[str, str]
    missing_entities: Set[str]
    unexpected_entities: Set[str]
    recall: float  # % expected entities found
    precision: float  # % found entities that are expected
    f1_score: float  # Harmonic mean of recall/precision
    execution_time: float
    error_message: str = ""


@dataclass
class ModelResult:
    """Aggregated results for a model"""

    model_name: str
    total_tests: int
    successful_tests: int
    avg_recall: float
    avg_precision: float
    avg_f1_score: float
    avg_execution_time: float
    results_by_level: Dict[str, Dict[str, float]]
    failed_tests: List[str]


class AnonymizationEvaluator:
    def __init__(
        self,
        dataset_file: str = "evaluation_datasets.json",
        enable_multithreading: bool = False,
        max_workers: int = 3,
    ):
        """
        Initialize the evaluator

        Args:
            dataset_file: JSON file with tests and models
            enable_multithreading: Enable parallelism to test multiple models
            max_workers: Max number of threads (beware of LLM server limits)
        """
        self.dataset_file = dataset_file
        self.enable_multithreading = enable_multithreading
        self.max_workers = max_workers
        self.results: List[TestResult] = []

        # Load datasets
        with open(dataset_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        print(f"📊 Loaded {len(self.data['test_cases'])} test cases")
        print(f"🤖 {len(self.data['models_to_test'])} models to evaluate")
        print(
            f"🧵 Multithreading: {'✅ Enabled' if enable_multithreading else '❌ Disabled'}"
        )

    def normalize_entity(self, entity: str) -> str:
        """Normalize an entity for comparison (remove spaces, case)"""
        return entity.strip().lower()

    def extract_entities_from_mapping(self, mapping: Dict[str, str]) -> Dict[str, str]:
        """Extract anonymized entities from the mapping returned by PromptSan"""
        entities = {}
        for original, token in mapping.items():
            # Extract label from token (__LABEL_N__ -> LABEL)
            if token.startswith("__") and token.endswith("__"):
                parts = token[2:-2].split("_")
                if len(parts) >= 2:
                    label = "_".join(
                        parts[:-1]
                    )  # Everything except last element (number)
                    entities[original] = label
        return entities

    def calculate_metrics(
        self, found: Dict[str, str], expected: Dict[str, str]
    ) -> Tuple[float, float, float, Set[str], Set[str]]:
        """
        Calculate performance metrics

        Returns:
            recall, precision, f1_score, missing_entities, unexpected_entities
        """
        # Normalize keys for comparison
        found_normalized = {self.normalize_entity(k): v for k, v in found.items()}
        expected_normalized = {self.normalize_entity(k): v for k, v in expected.items()}

        # Found and expected entities
        found_keys = set(found_normalized.keys())
        expected_keys = set(expected_normalized.keys())

        # Calculations
        true_positives = len(found_keys & expected_keys)
        missing_entities = expected_keys - found_keys
        unexpected_entities = found_keys - expected_keys

        # Metrics
        recall = true_positives / len(expected_keys) if expected_keys else 1.0
        precision = true_positives / len(found_keys) if found_keys else 1.0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return recall, precision, f1_score, missing_entities, unexpected_entities

    def test_single_case(self, test_case: Dict, model_config: Dict) -> TestResult:
        """Test a single case with a model"""
        test_id = test_case["id"]
        model_name = model_config["name"]

        try:
            start_time = time.time()

            # Load prompt template from file or use direct template
            prompt_template = None
            if "prompt_template_file" in model_config:
                try:
                    with open(
                        model_config["prompt_template_file"], "r", encoding="utf-8"
                    ) as f:
                        prompt_template = f.read()
                except FileNotFoundError:
                    raise ValueError(
                        f"Prompt template file not found: {model_config['prompt_template_file']}"
                    )
            else:
                prompt_template = model_config.get("prompt_template")

            if not prompt_template:
                raise ValueError("No prompt template specified in model config")

            # PromptSan configuration
            config = SanConfig(
                strategies=["llm"],
                llm_model=model_config["name"],
                llm_base_url=model_config["base_url"],
                llm_prompt_template=prompt_template,
            )

            sanitizer = PromptSanitizer(config)

            # Anonymization
            result = sanitizer.anonymize(test_case["text"])
            execution_time = time.time() - start_time

            # Extract found entities
            found_entities = self.extract_entities_from_mapping(result.mapping)
            expected_entities = test_case["expected_entities"]

            # Calculate metrics
            recall, precision, f1_score, missing, unexpected = self.calculate_metrics(
                found_entities, expected_entities
            )

            return TestResult(
                test_id=test_id,
                model_name=model_name,
                success=True,
                found_entities=found_entities,
                expected_entities=expected_entities,
                missing_entities=missing,
                unexpected_entities=unexpected,
                recall=recall,
                precision=precision,
                f1_score=f1_score,
                execution_time=execution_time,
            )

        except Exception as e:
            return TestResult(
                test_id=test_id,
                model_name=model_name,
                success=False,
                found_entities={},
                expected_entities=test_case["expected_entities"],
                missing_entities=set(test_case["expected_entities"].keys()),
                unexpected_entities=set(),
                recall=0.0,
                precision=0.0,
                f1_score=0.0,
                execution_time=0.0,
                error_message=str(e),
            )

    def run_evaluation_single_threaded(self) -> List[TestResult]:
        """Execute evaluation in single-thread mode"""
        results = []
        total_tests = len(self.data["test_cases"]) * len(self.data["models_to_test"])
        current = 0

        for model_config in self.data["models_to_test"]:
            print(f"\n🤖 Testing model: {model_config['name']}")

            for test_case in self.data["test_cases"]:
                current += 1
                print(
                    f"  [{current}/{total_tests}] Testing {test_case['id']} ({test_case['level']})...",
                    end=" ",
                )

                result = self.test_single_case(test_case, model_config)
                results.append(result)

                if result.success:
                    print(
                        f"✅ F1: {result.f1_score:.2f} ({result.execution_time:.1f}s)"
                    )
                else:
                    print(f"❌ Error: {result.error_message}")

        return results

    def run_evaluation_multi_threaded(self) -> List[TestResult]:
        """Execute evaluation in multi-thread mode"""
        results = []
        total_tests = len(self.data["test_cases"]) * len(self.data["models_to_test"])

        print(
            f"\n🧵 Starting multi-threaded evaluation with {self.max_workers} workers"
        )

        # Create all tasks
        tasks = []
        for model_config in self.data["models_to_test"]:
            for test_case in self.data["test_cases"]:
                tasks.append((test_case, model_config))

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self.test_single_case, test_case, model_config): (
                    test_case["id"],
                    model_config["name"],
                )
                for test_case, model_config in tasks
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_task):
                test_id, model_name = future_to_task[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result.success else "❌"
                    score = (
                        f"F1: {result.f1_score:.2f}"
                        if result.success
                        else f"Error: {result.error_message[:30]}"
                    )
                    print(
                        f"  [{completed}/{total_tests}] {model_name} | {test_id} | {status} {score}"
                    )

                except Exception as e:
                    print(
                        f"  [{completed}/{total_tests}] {model_name} | {test_id} | ❌ Exception: {str(e)}"
                    )

        return results

    def run_evaluation(self) -> List[TestResult]:
        """Execute complete evaluation"""
        print(
            f"\n🚀 Starting evaluation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if self.enable_multithreading and len(self.data["models_to_test"]) > 1:
            results = self.run_evaluation_multi_threaded()
        else:
            results = self.run_evaluation_single_threaded()

        self.results = results
        return results

    def aggregate_results_by_model(self) -> Dict[str, ModelResult]:
        """Aggregate results by model"""
        model_results = {}

        for model_config in self.data["models_to_test"]:
            model_name = model_config["name"]
            model_tests = [r for r in self.results if r.model_name == model_name]

            if not model_tests:
                continue

            successful_tests = [r for r in model_tests if r.success]
            failed_tests = [r.test_id for r in model_tests if not r.success]

            # Global metrics
            avg_recall = (
                sum(r.recall for r in successful_tests) / len(successful_tests)
                if successful_tests
                else 0
            )
            avg_precision = (
                sum(r.precision for r in successful_tests) / len(successful_tests)
                if successful_tests
                else 0
            )
            avg_f1_score = (
                sum(r.f1_score for r in successful_tests) / len(successful_tests)
                if successful_tests
                else 0
            )
            avg_execution_time = (
                sum(r.execution_time for r in successful_tests) / len(successful_tests)
                if successful_tests
                else 0
            )

            # Results by difficulty level
            results_by_level = {}
            for level in ["easy", "medium", "hard"]:
                level_tests = [
                    r
                    for r in successful_tests
                    if any(
                        tc["level"] == level and tc["id"] == r.test_id
                        for tc in self.data["test_cases"]
                    )
                ]
                if level_tests:
                    results_by_level[level] = {
                        "count": len(level_tests),
                        "avg_recall": sum(r.recall for r in level_tests)
                        / len(level_tests),
                        "avg_precision": sum(r.precision for r in level_tests)
                        / len(level_tests),
                        "avg_f1_score": sum(r.f1_score for r in level_tests)
                        / len(level_tests),
                    }

            model_results[model_name] = ModelResult(
                model_name=model_name,
                total_tests=len(model_tests),
                successful_tests=len(successful_tests),
                avg_recall=avg_recall,
                avg_precision=avg_precision,
                avg_f1_score=avg_f1_score,
                avg_execution_time=avg_execution_time,
                results_by_level=results_by_level,
                failed_tests=failed_tests,
            )

        return model_results

    def print_summary(self, model_results: Dict[str, ModelResult]):
        """Display a summary of results"""
        print(f"\n" + "=" * 80)
        print(f"📊 EVALUATION SUMMARY")
        print(f"=" * 80)

        for model_name, result in model_results.items():
            print(f"\n🤖 Model: {model_name}")
            print(
                f"   Tests: {result.successful_tests}/{result.total_tests} successful ({result.successful_tests/result.total_tests*100:.1f}%)"
            )
            print(f"   Avg Recall: {result.avg_recall:.3f} (% expected entities found)")
            print(
                f"   Avg Precision: {result.avg_precision:.3f} (% found entities that were expected)"
            )
            print(f"   Avg F1-Score: {result.avg_f1_score:.3f} (harmonic mean)")
            print(f"   Avg Time: {result.avg_execution_time:.2f}s per test")

            if result.results_by_level:
                print(f"   By difficulty:")
                for level, stats in result.results_by_level.items():
                    print(
                        f"     {level.capitalize()}: F1={stats['avg_f1_score']:.3f} ({stats['count']} tests)"
                    )

            if result.failed_tests:
                print(f"   ❌ Failed tests: {', '.join(result.failed_tests)}")

    def save_detailed_results(self, filename: str = None):
        """Save detailed results to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"

        # Prepare data for JSON
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "dataset_file": self.dataset_file,
            "multithreading_enabled": self.enable_multithreading,
            "total_tests": len(self.results),
            "models_tested": list(set(r.model_name for r in self.results)),
            "results": [],
        }

        for result in self.results:
            export_data["results"].append(
                {
                    "test_id": result.test_id,
                    "model_name": result.model_name,
                    "success": result.success,
                    "recall": result.recall,
                    "precision": result.precision,
                    "f1_score": result.f1_score,
                    "execution_time": result.execution_time,
                    "found_entities": result.found_entities,
                    "expected_entities": result.expected_entities,
                    "missing_entities": list(result.missing_entities),
                    "unexpected_entities": list(result.unexpected_entities),
                    "error_message": result.error_message,
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Detailed results saved to: {filename}")
        return filename


def main():
    """Main function"""
    print("🔬 PromptSan Anonymization Evaluation Tool")
    print("=" * 50)

    # Configuration
    enable_multithreading = (
        input("Enable multithreading? (y/N): ").lower().startswith("y")
    )
    max_workers = 3
    if enable_multithreading:
        try:
            max_workers = int(
                input(f"Max workers (default {max_workers}): ") or max_workers
            )
        except ValueError:
            pass

    # Create and run evaluator
    evaluator = AnonymizationEvaluator(
        enable_multithreading=enable_multithreading, max_workers=max_workers
    )

    # Execute evaluation
    start_time = time.time()
    results = evaluator.run_evaluation()
    total_time = time.time() - start_time

    # Analyze results
    model_results = evaluator.aggregate_results_by_model()
    evaluator.print_summary(model_results)

    print(f"\n⏱️  Total evaluation time: {total_time:.1f}s")
    print(f"📊 Total tests executed: {len(results)}")

    # Save
    save_results = input("\nSave detailed results to JSON? (Y/n): ").lower()
    if not save_results.startswith("n"):
        evaluator.save_detailed_results()

    print("\n✅ Evaluation completed!")


if __name__ == "__main__":
    main()
