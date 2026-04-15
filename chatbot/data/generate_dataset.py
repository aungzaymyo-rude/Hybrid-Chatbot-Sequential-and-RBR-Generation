from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _load_jsonl(path: Path) -> List[dict[str, str]]:
    rows: List[dict[str, str]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _dedupe(rows: Iterable[dict[str, str]]) -> List[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    output: List[dict[str, str]] = []
    for row in rows:
        key = (_normalize_text(row.get("text", "")), row.get("intent", ""))
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "text": row["text"],
            "intent": row["intent"],
            "lang": row.get("lang", "en"),
        })
    return output


def _existing_counts(rows: Iterable[dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        intent = row.get("intent")
        if not intent:
            continue
        counts[intent] = counts.get(intent, 0) + 1
    return counts


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "train" / "intent_dataset.jsonl"

NAMES = ["Alex", "Maya", "Liam", "Noah", "Ava", "Emma"]
CITIES = ["Yangon", "Mandalay", "Bangkok", "Tokyo", "Paris", "Madrid"]
DAYS = ["today", "tomorrow", "this week", "next Monday"]
TIMES = ["9am", "2pm", "6pm", "7:30pm"]

TEMPLATES = {
    "greeting": [
        "hello",
        "hi there",
        "good morning",
        "good evening",
        "hey, how are you",
        "hello, I am {name}",
        "hi, can you help me",
        "greetings",
        "hey chatbot",
        "hello from {city}",
        "hey, nice to meet you",
        "hi, I have a question",
    ],
    "help": [
        "I need help with hematology lab procedures",
        "can you assist me with a CBC question",
        "help me understand sample collection",
        "I am stuck with lab workflow",
        "can you explain how this works in hematology",
        "I need assistance with CBC testing",
        "please help with hematology lab steps",
        "support request for {name}",
        "can you guide me on hematology",
        "I need help in {city} lab",
        "please help",
        "I need guidance on specimen handling",
    ],
    "cbc_info": [
        "what is a CBC",
        "explain complete blood count",
        "what does a CBC include",
        "which parameters are in a CBC",
        "what is hemoglobin in a CBC",
        "what is hematocrit",
        "what is RBC count",
        "what is WBC count",
        "what is platelet count",
        "what are the parts of a CBC",
        "CBC test overview",
        "CBC basics for {name}",
        "can you describe CBC results",
        "reference ranges for CBC",
        "what does a CBC measure",
        "why is a CBC ordered",
        "difference between CBC and differential",
        "what is MCV",
        "what is MCHC",
        "what is RDW",
    ],
    "sample_collection": [
        "which tube is used for CBC",
        "EDTA tube for CBC",
        "how do I collect blood for CBC",
        "how many inversions for EDTA tube",
        "specimen handling for CBC",
        "how to label a CBC specimen",
        "what is the correct fill volume for EDTA",
        "how to prevent hemolysis during collection",
        "sample collection steps for hematology",
        "what is lavender top tube used for",
        "how to store a CBC sample",
        "transport requirements for CBC samples",
        "can I use heparin tube for CBC",
        "blood draw order of tubes for CBC",
        "how long is CBC sample stable",
        "mixing EDTA tube after collection",
        "specimen rejection criteria for CBC",
        "clotted sample in EDTA tube",
        "how to handle insufficient volume",
        "what is the proper anticoagulant for CBC",
    ],
    "rbc_term": [
        "what is RBC count",
        "explain red blood cell count",
        "what does RBC mean in hematology",
        "what is erythrocyte count",
        "what does low RBC suggest",
        "what does high RBC suggest",
        "what is anemia screening with RBC",
        "how is RBC count interpreted",
        "what is red cell count in CBC",
        "can you explain RBC values",
        "what does RBC tell us for {name}",
        "how should {name} understand RBC count",
        "what is the role of RBC in CBC review",
        "how do you explain RBC count in {city} lab training",
        "what can cause low RBC in screening",
        "what can cause raised RBC count",
        "what RBC term should I know for hematology",
        "how is RBC count reported in CBC",
        "what does erythrocyte mean on a CBC report",
        "can you define RBC count simply",
    ],
    "wbc_term": [
        "what is WBC count",
        "explain white blood cell count",
        "what does leukocyte count mean",
        "what is leukocytosis",
        "what is leukopenia",
        "what does high WBC suggest",
        "what does low WBC suggest",
        "how is WBC count interpreted",
        "what is differential white cell count",
        "can you explain WBC values",
        "what does WBC tell us for {name}",
        "how should {name} understand leukocyte count",
        "what is the purpose of WBC review in hematology",
        "how do you explain WBC count in {city} lab training",
        "what can cause a raised white cell count",
        "what can cause a low white cell count",
        "what WBC term should I know for CBC review",
        "how is WBC count reported on a CBC",
        "what does leukocyte mean on the report",
        "can you define WBC count simply",
    ],
    "coag_test": [
        "what is PT test",
        "what is aPTT",
        "explain coagulation screening",
        "what does INR mean",
        "which tube is used for coagulation tests",
        "how should coag samples be collected",
        "what does prolonged PT suggest",
        "what does prolonged aPTT suggest",
        "how is citrate tube filled for coag tests",
        "what are common coagulation tests",
        "how do you explain PT for {name}",
        "what does INR show in coag review",
        "how should {name} collect a citrate sample",
        "what is the light blue tube used for",
        "how do coag tests fit into hematology workflow",
        "what are screening coag assays in {city} lab",
        "what happens if citrate tube is underfilled",
        "how is PT INR reported",
        "what does a long clotting time suggest",
        "can you summarize coag sample requirements",
    ],
    "blood_smear": [
        "what is a peripheral blood smear",
        "why is blood smear examination done",
        "how do you prepare a blood film",
        "what stains are used for blood smear",
        "what can a blood smear show",
        "when is smear review required",
        "what is wedge smear technique",
        "how should a blood smear be labeled",
        "what are blood smear artifacts",
        "can you explain peripheral smear review",
        "how do you teach smear review to {name}",
        "what should {name} know about blood film preparation",
        "how is a smear made in {city} hematology lab",
        "what is the feathered edge on a blood smear",
        "what are common smear preparation errors",
        "when should a CBC trigger smear review",
        "what does morphology review mean on a smear",
        "how should a peripheral smear slide be handled",
        "what does smear staining help you see",
        "can you summarize blood smear workflow",
    ],
    "capability_query": [
        "what can you do",
        "how can you help",
        "what questions can i ask",
        "what do you support in hematology",
        "can you tell me your scope",
        "what can you answer for {name}",
        "what topics do you cover in {city} lab",
        "can you help with coag and cbc",
        "what is your role in hematology workflow",
        "can you explain what this assistant does",
        "what can you do for {name}",
        "how can you help in {city} lab",
        "what topics do you support this {day}",
        "what tests can you explain at {time}",
        "can you answer rbc and wbc questions",
        "can you explain coag and smear questions",
        "what is your medical lab scope",
        "what hematology tasks can you support",
        "what kind of questions should {name} ask you",
        "can you describe your capabilities simply",
    ],
    "thanks": [
        "thank you",
        "thanks",
        "thanks for your help",
        "thank you very much",
        "appreciate it",
        "many thanks",
        "thanks assistant",
        "that helps a lot",
        "great thanks",
        "okay thank you",
        "thank you {name}",
        "many thanks for the explanation",
        "thanks for the hematology help",
        "that was useful thanks",
        "thanks for clarifying this",
        "thank you for the sample collection guidance",
        "thanks for the coagulation explanation",
        "thanks for the blood smear summary",
        "i appreciate the help today",
        "thank you for your support",
    ],
    "goodbye": [
        "bye",
        "goodbye",
        "see you",
        "talk to you later",
        "bye for now",
        "see you later",
        "thanks bye",
        "good night",
        "catch you later",
        "have a good day",
        "bye {name}",
        "see you later assistant",
        "goodbye for now",
        "i will come back later",
        "talk again this {day}",
        "have a good shift",
        "thanks see you soon",
        "bye and take care",
        "ending chat now",
        "that is all for now",
    ],
    "clarification": [
        "can you explain again",
        "i do not understand",
        "what do you mean",
        "please clarify that",
        "can you say that in a simpler way",
        "explain it again for {name}",
        "i need a clearer explanation",
        "what does that mean exactly",
        "can you repeat that",
        "please break it down",
        "can you explain that to {name}",
        "please simplify this answer",
        "say that another way",
        "what does this term mean exactly",
        "i still do not understand the point",
        "can you make that clearer",
        "repeat the explanation please",
        "explain it step by step",
        "what are you trying to say",
        "can you clarify the result term",
    ],
    "out_of_scope": [
        "tell me a joke",
        "what is football",
        "who won the movie award",
        "how is the weather today",
        "write me a poem",
        "what is the capital of france",
        "teach me guitar chords",
        "who are the best singers",
        "what is quantum physics",
        "recommend a restaurant",
        "tell me the latest celebrity news",
        "who is the president now",
        "help me with my math homework",
        "what phone should i buy",
        "how do i cook rice",
        "what is the best movie this year",
        "can you book a hotel for me",
        "teach me programming in python",
        "what is bitcoin price",
        "who won the football match",
    ],
    "unsafe_medical_request": [
        "how do i inject human body",
        "what drug should i give for anemia",
        "how do i treat leukemia",
        "tell me the dose for this patient",
        "how do i prescribe medicine",
        "what injection should i give now",
        "can you diagnose this patient",
        "what treatment should i start",
        "which antibiotic should i use",
        "how do i manage this patient's disease",
        "what medicine should i prescribe to {name}",
        "tell me the dose to give right now",
        "how should i inject this patient",
        "which drug should i start today",
        "how do i cure this disease",
        "can you choose treatment for this patient",
        "tell me the correct injection dose",
        "what medication should i order now",
        "how do i treat bleeding in a patient",
        "please diagnose this illness for me",
    ],
    "incomplete_query": [
        "what",
        "what is",
        "how",
        "why",
        "which one",
        "can you",
        "help?",
        "?",
        "???",
        "explain",
        "what now",
        "how now",
        "which test",
        "what does",
        "why is that",
        "can you help?",
        "what about this",
        "how about that",
        "which one is it",
        "what next",
    ],
    "fallback": [
        "asdf qwerty",
        "random string 12345",
        "tell me about quantum bananas",
        "blorp blorp",
        "this is unrelated",
        "nonsense input",
        "zxqv",
        "gibberish text",
        "what is 7 + purple",
        "???",
        "lorem ipsum",
        "blue sandwich",
    ],
}

SLOTS = {
    "name": NAMES,
    "city": CITIES,
    "day": DAYS,
    "time": TIMES,
}


def _fill_template(template: str, index: int) -> str:
    return template.format(
        name=SLOTS["name"][index % len(SLOTS["name"])],
        city=SLOTS["city"][index % len(SLOTS["city"])],
        day=SLOTS["day"][index % len(SLOTS["day"])],
        time=SLOTS["time"][index % len(SLOTS["time"])],
    )


def _generate_samples(intent: str, target: int, start_index: int = 0) -> List[dict[str, str]]:
    templates = TEMPLATES[intent]
    samples: List[dict[str, str]] = []
    index = start_index
    while len(samples) < target:
        template = templates[index % len(templates)]
        text = _fill_template(template, index)
        samples.append({"text": text, "intent": intent, "lang": "en"})
        index += 1
    return samples


def _parse_intents(raw: str | None) -> List[str]:
    if not raw:
        return list(TEMPLATES.keys())
    requested = [item.strip() for item in raw.split(",") if item.strip()]
    return [intent for intent in requested if intent in TEMPLATES]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic dataset for intents")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Existing dataset JSONL. Generation starts after the existing sample count per intent.",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine newly generated rows with --base and write one merged dataset.",
    )
    parser.add_argument("--per-intent", type=int, default=60)
    parser.add_argument("--fallback-count", type=int, default=None)
    parser.add_argument("--intents", type=str, default=None, help="Comma-separated list of intents")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it exists")
    args = parser.parse_args()

    random.seed(args.seed)
    intents = _parse_intents(args.intents)
    per_intent = max(1, int(args.per_intent))
    fallback_count = args.fallback_count
    base_rows = _load_jsonl(Path(args.base).resolve()) if args.base else []
    existing_counts = _existing_counts(base_rows)

    new_rows: List[dict[str, str]] = []
    for intent in intents:
        count = per_intent
        if intent == "fallback" and fallback_count is not None:
            count = max(1, int(fallback_count))
        new_rows.extend(_generate_samples(intent, count, start_index=existing_counts.get(intent, 0)))

    data = _dedupe([*base_rows, *new_rows]) if args.combine else new_rows
    random.shuffle(data)

    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = "_combined" if args.combine else "_generated"
        output_path = output_path.with_name(f"{output_path.stem}{suffix}_{timestamp}{output_path.suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in data:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    if args.combine and args.base:
        print(f"Base rows: {len(base_rows)}")
        print(f"Requested new rows: {len(new_rows)}")
        print(f"Merged unique rows: {len(data)}")
    else:
        print(f"Generated rows: {len(data)}")
    print(f"Wrote dataset to {output_path}")


if __name__ == "__main__":
    main()
