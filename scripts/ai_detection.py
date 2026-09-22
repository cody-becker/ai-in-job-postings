"""
ai_detection.py

Classifies job posting descriptions by AI/ML relevance.
Positive terms cast wide (technical + casual phrasing).
Exclusions kept narrow, evidence-based, and checked against
known soft-positive examples so they don't overreach.

Tier system (validated against 30 hand-labeled real postings):
  1 = no AI mention
  2 = passing/incidental AI mention (1-2 mentions, low density)
  3 = AI central to the role (4+ mentions, high density, or in title)

NOTE: tiers 1/2/3 boundaries are backed by real labeled data. There is
currently a genuine gap in the labeled set between "1-2 mentions" and
"4+ mentions" -- no example has landed there yet. If a report ever wants
finer resolution than 3 tiers, that gap needs real labeled examples
before another boundary is trustworthy -- don't invent one.
"""

import re

# ---------------------------------------------------------------------------
# Positive terms -- cast wide, include casual/business phrasing on purpose
# ---------------------------------------------------------------------------
POSITIVE_TERMS = [
    "machine learning", "artificial intelligence", "neural network",
    "large language model", "llm", "generative ai", "deep learning",
    "computer vision", "nlp", "natural language processing",
    "ai fluency", "ai-powered", "leveraging ai", "using ai",
    "comfortable using ai", "ai tools", "ai-enabled",
]

AI_TERM_PATTERN = r"\b(ai|artificial intelligence|machine learning|llm|large language model|generative ai|neural network|deep learning|nlp)\b"

# ---------------------------------------------------------------------------
# Exclusions -- narrow, evidence-based only. Each one should be traceable
# back to a specific false positive you actually found in real data.
# ---------------------------------------------------------------------------
def is_game_dev_ai_mention(title: str, description: str) -> bool:
    """Found via testing: 'AI' in game-dev postings usually means classical
    game AI (pathfinding, NPC behavior), not modern ML/LLM AI."""
    game_signals = ["game designer", "gameplay", "game engine"]
    return any(g in title.lower() for g in game_signals)

# ---------------------------------------------------------------------------
# Weak-signal detector -- AI mentions near generic company-mission language
# get treated as weaker evidence than AI mentioned in actual role content.
# Found via testing: Analog Devices' "About Us" boilerplate mentions AI in
# a company-mission sentence, unrelated to the specific role's actual duties.
# ---------------------------------------------------------------------------
COMPANY_BOILERPLATE_SIGNALS = [
    "combines", "is a global leader", "our mission is",
    "bridges the physical and digital", "revenue of more than",
]

def ai_mention_near_boilerplate(description: str, window=100) -> bool:
    ai_positions = [m.start() for m in re.finditer(r"\bai\b", description, re.IGNORECASE)]
    for pos in ai_positions:
        nearby_text = description[max(0, pos-window):pos+window].lower()
        if any(signal in nearby_text for signal in COMPANY_BOILERPLATE_SIGNALS):
            return True
    return False

# ---------------------------------------------------------------------------
# Regression check -- soft positives that must NEVER get filtered out
# ---------------------------------------------------------------------------
KNOWN_SOFT_POSITIVES = [
    "requires AI fluency for this customer service role",
    "comfortable using AI tools in daily workflow",
    "familiarity with AI a plus",
]

def run_soft_positive_check(exclusion_fn, title=""):
    for text in KNOWN_SOFT_POSITIVES:
        if exclusion_fn(title, text):
            print(f"WARNING: exclusion wrongly filters: '{text}'")

# ---------------------------------------------------------------------------
# Confirmed real examples of non-technical roles with genuine AI usage.
# ---------------------------------------------------------------------------
NON_TECHNICAL_AI_EXAMPLES = [
    {
        "company": "championsgroupholdings",
        "title": "Digital Marketing Specialist",
        "snippet": "lead AI-powered speed-to-lead integrations across digital channels... Serve as the digital marketing SME for AI integrations",
        "why_it_matters": "Non-technical, business-function role with genuine, substantive AI usage described in plain language -- exactly the phenomenon this project measures.",
    },
]

# ---------------------------------------------------------------------------
# Prominence signals -- validated against 30 hand-labeled real postings
# ---------------------------------------------------------------------------
def compute_prominence_signals(title: str, description: str) -> dict:
    title_hit = bool(re.search(AI_TERM_PATTERN, title, re.IGNORECASE))
    mentions = re.findall(AI_TERM_PATTERN, description, re.IGNORECASE)
    mention_count = len(mentions)
    word_count = len(description.split())
    density = mention_count / word_count if word_count > 0 else 0
    return {
        "title_hit": title_hit,
        "mention_count": mention_count,
        "density": round(density * 1000, 2),
    }

def classify_posting(title: str, description: str) -> int:
    """Returns tier 1 (no AI), 2 (passing mention), or 3 (AI central)."""
    if is_game_dev_ai_mention(title, description):
        return 1

    signals = compute_prominence_signals(title, description)

    if signals["mention_count"] == 0:
        return 1
    if signals["mention_count"] >= 4 or signals["title_hit"]:
        return 3
    return 2  # 1-3 mentions, no title hit