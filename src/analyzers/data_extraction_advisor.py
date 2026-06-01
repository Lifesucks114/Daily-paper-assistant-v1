import re
from typing import Any


PATTERNS = {
    "temperature": r"(\d{2,3}\s?°?C)",
    "reaction_time": r"(\d+(\.\d+)?\s?(min|minutes|h|hours))",
    "pH": r"pH\s?(\d+(\.\d+)?)",
    "solid_liquid_ratio": r"(\d+:\d+\s?(w/v|g/mL|g/ml)?)",
    "yield": r"(\d+(\.\d+)?\s?%(\s?(yield|recovery))?)",
}


def infer_experimental_info(paper: dict[str, Any]) -> dict[str, Any]:
    text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
    lower = text.lower()
    info: dict[str, Any] = {}

    biomass_terms = ["tomato stalk", "tomato stem", "cucumber stalk", "wheat straw", "corn stover", "bagasse"]
    method_terms = ["acid hydrolysis", "enzymatic hydrolysis", "pretreatment", "autohydrolysis", "hydrothermal"]
    separation_terms = ["membrane", "ultrafiltration", "nanofiltration", "chromatography", "purification"]

    info["biomass_type"] = [term for term in biomass_terms if term in lower]
    info["pretreatment_method"] = [term for term in method_terms if term in lower]
    info["acid_enzyme_type"] = [term for term in ["sulfuric acid", "hydrochloric acid", "acetic acid", "xylanase", "cellulase"] if term in lower]
    info["separation_method"] = [term for term in separation_terms if term in lower]
    info["HPLC_column"] = ""
    info["mobile_phase"] = ""
    info["flow_rate"] = ""
    info["detector"] = ""
    info["XOS_DP_distribution"] = ""
    info["monosaccharide_composition"] = ""

    for key, pattern in PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        info[key] = match.group(1) if match else ""

    return info
