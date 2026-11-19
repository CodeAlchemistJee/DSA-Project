import random

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Ananya", "Diya", "Myra", "Aadhya", "Anvi", "Pari",
    "Navya", "Saanvi", "Kiara", "Riya", "Rohan", "Kabir", "Siddharth", "Nikhil",
    "Pooja", "Neha", "Shruti", "Karan", "Varun", "Meera", "Tanvi", "Harsh"
]

LAST_NAMES = [
    "Sharma", "Verma", "Tiwari", "Patel", "Reddy", "Nair", "Iyer", "Gupta",
    "Joshi", "Kulkarni", "Mehta", "Malhotra", "Kapoor", "Chauhan", "Mishra",
    "Yadav", "Das", "Banerjee", "Singh", "Rao"
]

TECH_PREFIXES = [
    "app", "auto", "data", "cloud", "code", "net", "cyber", "micro", "hyper",
    "meta", "algo", "sync", "dev", "stack", "stream", "smart", "quant", "edge"
]

TECH_SUFFIXES = [
    "ly", "ify", "hub", "lab", "base", "flow", "grid", "core", "sync", "cast",
    "mind", "nest", "pulse", "scape", "works", "zone", "craft", "link", "bit", "forge"
]

BASE_WORDS = [
    "apple", "application", "apricot", "aptitude", "architecture", "algorithm",
    "array", "avocado", "atlas", "aurora", "automation", "analytics", "address",
    "agenda", "airport", "alarm", "album", "anchor", "angel", "animal", "ant",
    "apartment", "apology", "appeal", "appear", "appointment", "archive", "area",
    "arena", "arrow", "article", "artist", "aspect", "asset", "assistant",
    "astronomy", "athlete", "atom", "attack", "attempt", "attend", "attention",
    "attitude", "audio", "audit", "author", "autumn", "avatar", "avenue", "award"
]

def build_records(target_count=5600):
    rng = random.Random(42)
    records = {}

    # 1. Seed core dictionary words with realistic weights
    for w in BASE_WORDS:
        records[w.lower()] = (w, rng.randint(25, 100))

    # 2. Generate contacts (full names + name + phone tags)
    for fn in FIRST_NAMES:
        for ln in LAST_NAMES:
            full_name = f"{fn} {ln}"
            key = full_name.lower()
            if key not in records:
                records[key] = (full_name, rng.randint(5, 95))

            phone_tag = f"{fn} ({rng.randint(7000000000, 9999999999)})"
            pkey = phone_tag.lower()
            if pkey not in records and len(records) < target_count:
                records[pkey] = (phone_tag, rng.randint(1, 60))

    # 3. Generate compound/domain words so prefixes like "app" have rich matches
    for p in TECH_PREFIXES:
        for s in TECH_SUFFIXES:
            for idx in range(1, 15):
                word = f"{p}{s}{idx if idx > 1 else ''}"
                key = word.lower()
                if key not in records:
                    records[key] = (word, rng.randint(1, 90))
                if len(records) >= target_count:
                    break
            if len(records) >= target_count:
                break
        if len(records) >= target_count:
            break

    return list(records.values())

def main():
    items = build_records(5600)
    with open("dataset.txt", "w", encoding="utf-8") as f:
        for word, weight in items:
            f.write(f"{weight}\t{word}\n")
    print(f"Generated {len(items)} records in dataset.txt")

if __name__ == "__main__":
    main()