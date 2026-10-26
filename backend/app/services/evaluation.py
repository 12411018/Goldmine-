"""
Goldmine AI — Evaluation Engine

Evaluates multiple model responses using observable signals.
Calculates the Goldmine Score and selects the strongest response.
"""

import re
from typing import Optional
from app.adapters.base import GenerateResponse


class EvaluationResult:
    """Result of evaluating a single model response."""

    def __init__(
        self,
        model_id: str,
        content: str,
        latency_ms: int,
        cross_model_agreement: float = 0.0,
        evidence_support: float = 0.0,
        completeness: float = 0.0,
        relevance: float = 0.0,
        consistency: float = 0.0,
    ):
        self.model_id = model_id
        self.content = content
        self.latency_ms = latency_ms
        self.cross_model_agreement = cross_model_agreement
        self.evidence_support = evidence_support
        self.completeness = completeness
        self.relevance = relevance
        self.consistency = consistency

    @property
    def goldmine_score(self) -> float:
        """Calculate the overall Goldmine Score (0-100)."""
        weights = {
            "cross_model_agreement": 0.30,
            "completeness": 0.25,
            "relevance": 0.20,
            "consistency": 0.15,
            "evidence_support": 0.10,
        }
        score = (
            self.cross_model_agreement * weights["cross_model_agreement"]
            + self.completeness * weights["completeness"]
            + self.relevance * weights["relevance"]
            + self.consistency * weights["consistency"]
            + self.evidence_support * weights["evidence_support"]
        )
        return round(min(100, max(0, score)), 1)

    @property
    def signals(self) -> dict:
        return {
            "cross_model_agreement": round(self.cross_model_agreement, 1),
            "evidence_support": round(self.evidence_support, 1),
            "completeness": round(self.completeness, 1),
            "relevance": round(self.relevance, 1),
            "consistency": round(self.consistency, 1),
        }


class EvaluationEngine:
    """
    Evaluates model responses using observable signals.
    
    This is NOT a model's self-reported confidence.
    These are computed from comparing responses across models.
    """

    def evaluate_responses(
        self,
        responses: list[GenerateResponse],
        user_prompt: str,
    ) -> list[EvaluationResult]:
        """
        Evaluate all responses and return scored results.
        """
        if not responses:
            return []

        if len(responses) == 1:
            # Single model — can only evaluate completeness and relevance
            r = responses[0]
            return [
                EvaluationResult(
                    model_id=r.model_id,
                    content=r.content,
                    latency_ms=r.latency_ms,
                    cross_model_agreement=75.0,  # Neutral — no comparison possible
                    evidence_support=70.0,
                    completeness=self._score_completeness(r.content, user_prompt),
                    relevance=self._score_relevance(r.content, user_prompt),
                    consistency=75.0,
                )
            ]

        results = []
        contents = [r.content for r in responses]

        for i, response in enumerate(responses):
            other_contents = [c for j, c in enumerate(contents) if j != i]

            agreement = self._score_agreement(response.content, other_contents)
            completeness = self._score_completeness(response.content, user_prompt)
            relevance = self._score_relevance(response.content, user_prompt)
            consistency = self._score_consistency(response.content, other_contents)
            evidence = self._score_evidence(response.content)

            results.append(
                EvaluationResult(
                    model_id=response.model_id,
                    content=response.content,
                    latency_ms=response.latency_ms,
                    cross_model_agreement=agreement,
                    evidence_support=evidence,
                    completeness=completeness,
                    relevance=relevance,
                    consistency=consistency,
                )
            )

        return results

    def select_best(
        self, evaluations: list[EvaluationResult]
    ) -> tuple[EvaluationResult, str]:
        """
        Select the best response and generate a selection explanation.
        Returns (best_result, explanation).
        """
        if not evaluations:
            raise ValueError("No evaluations to select from")

        best = max(evaluations, key=lambda e: e.goldmine_score)

        explanation = self._generate_explanation(best, evaluations)
        return best, explanation

    def _score_agreement(self, content: str, other_contents: list[str]) -> float:
        """
        Score cross-model agreement by comparing key terms and structure.
        Higher score means this response agrees more with other models.
        """
        if not other_contents:
            return 75.0

        content_terms = self._extract_key_terms(content)
        if not content_terms:
            return 60.0

        agreement_scores = []
        for other in other_contents:
            other_terms = self._extract_key_terms(other)
            if not other_terms:
                agreement_scores.append(50.0)
                continue

            # Jaccard similarity on key terms
            intersection = content_terms & other_terms
            union = content_terms | other_terms
            similarity = len(intersection) / len(union) if union else 0

            # Scale to 50-100 range
            agreement_scores.append(50 + similarity * 50)

        return sum(agreement_scores) / len(agreement_scores)

    def _score_completeness(self, content: str, prompt: str) -> float:
        """
        Score response completeness based on length, structure, and coverage.
        """
        score = 50.0

        # Length contribution (longer is generally more complete, up to a point)
        word_count = len(content.split())
        if word_count > 50:
            score += 10
        if word_count > 150:
            score += 10
        if word_count > 300:
            score += 5
        if word_count > 800:
            score += 5

        # Structure: headers, lists, code blocks indicate organized response
        if re.search(r'^#{1,3}\s', content, re.MULTILINE):
            score += 5
        if re.search(r'^[-*]\s', content, re.MULTILINE):
            score += 5
        if '```' in content:
            score += 5

        # Does it address prompt keywords?
        prompt_terms = self._extract_key_terms(prompt)
        content_terms = self._extract_key_terms(content)
        if prompt_terms:
            coverage = len(prompt_terms & content_terms) / len(prompt_terms)
            score += coverage * 10

        return min(100, score)

    def _score_relevance(self, content: str, prompt: str) -> float:
        """
        Score how relevant the response is to the prompt.
        """
        prompt_terms = self._extract_key_terms(prompt)
        content_terms = self._extract_key_terms(content)

        if not prompt_terms:
            return 70.0

        # What fraction of prompt terms appear in the response?
        coverage = len(prompt_terms & content_terms) / len(prompt_terms)
        return 50 + coverage * 50

    def _score_consistency(self, content: str, other_contents: list[str]) -> float:
        """
        Score internal consistency and lack of contradictions.
        """
        if not other_contents:
            return 75.0

        # Check for contradiction indicators
        contradiction_phrases = [
            "however, this is incorrect",
            "actually, the opposite",
            "this contradicts",
            "not true",
            "incorrect",
        ]

        score = 85.0
        content_lower = content.lower()

        # Self-contradiction check
        for phrase in contradiction_phrases:
            if phrase in content_lower:
                score -= 5

        return max(40, min(100, score))

    def _score_evidence(self, content: str) -> float:
        """
        Score the presence of evidence and supporting details.
        """
        score = 55.0

        # Check for specific evidence patterns
        if re.search(r'\d{4}', content):  # Years or numbers
            score += 5
        if re.search(r'https?://', content):  # URLs
            score += 10
        if re.search(r'"[^"]{10,}"', content):  # Quotes
            score += 5
        if re.search(r'according to|research shows|studies|data', content, re.IGNORECASE):
            score += 10
        if re.search(r'for example|such as|e\.g\.|i\.e\.', content, re.IGNORECASE):
            score += 5
        if re.search(r'```', content):  # Code examples
            score += 10

        return min(100, score)

    def _extract_key_terms(self, text: str) -> set[str]:
        """Extract meaningful terms from text, filtering stop words."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "about", "like",
            "through", "after", "over", "between", "out", "against", "during",
            "without", "before", "under", "around", "among", "and", "but", "or",
            "not", "no", "nor", "so", "yet", "both", "either", "neither",
            "each", "every", "all", "any", "few", "more", "most", "other",
            "some", "such", "than", "too", "very", "just", "also", "now",
            "here", "there", "then", "when", "where", "why", "how", "what",
            "which", "who", "whom", "this", "that", "these", "those", "it",
            "its", "i", "you", "he", "she", "we", "they", "me", "him", "her",
            "us", "them", "my", "your", "his", "our", "their",
        }

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return {w for w in words if w not in stop_words}

    def _generate_explanation(
        self, best: EvaluationResult, all_results: list[EvaluationResult]
    ) -> str:
        """
        Generate a concise, observable explanation for why this model was selected.
        Never exposes chain-of-thought — only observable signals.
        """
        parts = []

        # Model name
        model_name = best.model_id.split("/")[-1] if "/" in best.model_id else best.model_id

        # Agreement
        if best.cross_model_agreement >= 80:
            parts.append("showed strong agreement with other models")
        elif best.cross_model_agreement >= 65:
            parts.append("had moderate agreement with other models")

        # Completeness
        if best.completeness >= 85:
            parts.append("produced a highly complete response")
        elif best.completeness >= 70:
            parts.append("provided a well-structured response")

        # Evidence
        if best.evidence_support >= 80:
            parts.append("included strong supporting evidence")
        elif best.evidence_support >= 65:
            parts.append("provided relevant supporting details")

        # Relevance
        if best.relevance >= 85:
            parts.append("was highly relevant to the question")

        if not parts:
            parts.append("scored highest overall among the evaluated models")

        explanation = f"{model_name} {', '.join(parts)}."

        if len(all_results) > 1:
            explanation += (
                f" This response was selected from {len(all_results)} models "
                f"based on evaluation of cross-model agreement, completeness, "
                f"relevance, and evidence support."
            )

        return explanation


# Singleton
evaluation_engine = EvaluationEngine()
