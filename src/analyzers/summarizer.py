import os
import json
from typing import Any

from openai import OpenAI


class OpenAISummarizer:
    def __init__(self, model: str, temperature: float, max_output_tokens: int, logger):
        self.model = os.getenv("OPENAI_MODEL", model)
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.logger = logger
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def summarize(
        self,
        paper: dict[str, Any],
        relevance_score: float,
        experimental_info: dict[str, Any],
        pdf_text: str = "",
    ) -> dict[str, Any]:
        if not self.client:
            self.logger.warning("OPENAI_API_KEY is not set; writing placeholder summaries.")
            return {
                "summary_zh": "未设置 OPENAI_API_KEY，已跳过自动摘要。",
                "summary_en": "OPENAI_API_KEY is not configured, so automatic summarization was skipped.",
                "relevance_score": relevance_score,
                "reason_for_relevance": "OpenAI not configured; used heuristic score.",
                "data_worth_extracting": "",
                "experimental_info": experimental_info,
            }

        prompt = self._prompt(paper, relevance_score, experimental_info, pdf_text)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a careful literature assistant for biomass conversion and hemicellulose/XOS research.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            return self._parse_json(content, relevance_score, experimental_info)
        except Exception:
            self.logger.exception("OpenAI summarization failed for %s", paper.get("title"))
            return {
                "summary_zh": "OpenAI 摘要失败，请查看日志。",
                "summary_en": "OpenAI summarization failed. Check logs for details.",
                "relevance_score": relevance_score,
                "reason_for_relevance": "OpenAI analysis failed; used heuristic score.",
                "data_worth_extracting": "",
                "experimental_info": experimental_info,
            }

    def _prompt(
        self,
        paper: dict[str, Any],
        relevance_score: float,
        experimental_info: dict[str, Any],
        pdf_text: str,
    ) -> str:
        return f"""
Analyze this paper for a researcher working on biomass conversion, hemicellulose extraction,
xylan/arabinoxylan, xylooligosaccharides (XOS), hydrolysis, HPLC sugar analysis, membrane
separation, and purification of oligosaccharides from agricultural residues.

Primary target: laboratory-scale XOS production from biomass-derived xylan or hemicellulose.
Be strict. General polysaccharide materials, biomedical gels, biochar, wastewater treatment,
generic biomass valorization, and unrelated catalysis should score 0-2 unless they directly
help produce, purify, quantify, or experimentally optimize XOS or xylan/hemicellulose hydrolysates.

Title: {paper.get("title", "")}
Journal: {paper.get("journal", "")}
DOI: {paper.get("doi", "")}
Abstract: {paper.get("abstract", "")}
Heuristic relevance score: {relevance_score}/5
Detected experimental information: {experimental_info}
PDF text excerpt, if available:
{pdf_text}

Return strict JSON only, no markdown fences, with these keys:
summary_zh: Chinese 3-5 bullet summary as one string.
summary_en: English 3-5 bullet summary as one string.
relevance_score: integer 0-5, where 0 unrelated; 1 only broad biomass/carbohydrate context; 2 adjacent method but not XOS production; 3 directly related to xylan/hemicellulose extraction, hydrolysis, XOS, or oligosaccharide purification/analysis; 4 highly relevant with lab conditions, yield, HPLC, DP distribution, or separation data; 5 directly reusable for XOS experimental design or dataset construction.
reason_for_relevance: concise reason.
data_worth_extracting: yes/no plus a short reason.
experimental_info: object with these keys:
biomass_type, pretreatment_method, acid_enzyme_type, temperature, reaction_time,
solid_liquid_ratio, pH, yield, XOS_DP_distribution, monosaccharide_composition,
HPLC_column, mobile_phase, flow_rate, detector, separation_method.
""".strip()

    def _parse_json(
        self,
        content: str,
        fallback_score: float,
        fallback_experimental: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                cleaned = cleaned.removeprefix("json").strip()
            data = json.loads(cleaned)
            data["summary_zh"] = data.get("summary_zh") or data.get("summary_cn") or ""
            data["summary_en"] = data.get("summary_en", "")
            data["relevance_score"] = data.get("relevance_score", fallback_score)
            data["experimental_info"] = data.get("experimental_info") or fallback_experimental
            return data
        except Exception:
            self.logger.warning("OpenAI returned non-JSON summary; storing raw content.")
            return {
                "summary_zh": content.strip(),
                "summary_en": "",
                "relevance_score": fallback_score,
                "reason_for_relevance": "OpenAI response was not JSON; used heuristic score.",
                "data_worth_extracting": "",
                "experimental_info": fallback_experimental,
            }
