from collections import defaultdict, Counter
import random
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import wordnet
from nltk.wsd import lesk
import urllib.parse
import re
from duckduckgo_search import DDGS
import subprocess

def make_coherent(text, model="phi3"):
    prompt = f"Make this text coherent, fix out of place synonyms, and correct awkward grammar, but don't change the core meaning. Rewrite this text so it is logical, grammatically correct, and reads like a human wrote it. Preserve the meaning, but reorganize sentences if needed for clarity:\n\n{text}"
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        return result.stdout.decode().strip()
    except Exception as e:
        print("Coherence model failed:", e)
        return text 

def pluralize(og, new):
    if og.lower() == "is":
        return new
    if og.isupper():
        new = new.capitalize()
        return new
    if og.endswith("ed"):
        return new + "ed"
    if og.lower().endswith("y") and not og.lower().endswith(("ay", "ey", "iy", "oy", "uy")):
        new = new[:-1]
        return new + "ies"
    if og.endswith("s"):
        return new + "s"
    return new

def get_synonym(word, context_sentence, pos=None):
    synset = lesk(context_sentence, word, pos=pos)
    if not synset:
        return word
    synonyms = [lemma.name().replace('_', ' ') for lemma in synset.lemmas() if lemma.name().lower() != word.lower()]
    if not synonyms:
        return word
    new = random.choice(synonyms)
    return pluralize(word, new)

def get_pos(tag):
    if tag.startswith("J"):
        return wordnet.ADJ
    elif tag.startswith("N"):
        return wordnet.NOUN
    elif tag.startswith("V"):
        return wordnet.VERB
    return None

def replace(words):
    if isinstance(words, str):
        words = words.split()
    tagged = nltk.pos_tag(words)
    new_words = []
    for i, (word, tag) in enumerate(tagged):
        if not word:
            continue
        wn_pos = get_pos(tag)
        if wn_pos in [wordnet.NOUN, wordnet.VERB, wordnet.ADJ]:
            if random.random() < 0.1:
                context = words[max(0, i-5): i+6]
                synonym = get_synonym(word, context, wn_pos)
                word = pluralize(word, synonym)
        new_words.append(word)
    return ' '.join(new_words) if new_words else ' '.join(words)

def build_ngram_chart(corpus, state_size=2):
    words = corpus.split()
    transitions = defaultdict(Counter)
    for i in range(len(words) - state_size):
        state = tuple(words[i:i + state_size])
        next_word = words[i + state_size]
        transitions[state][next_word] += 1
    return {state: {w: c / sum(counter.values()) for w, c in counter.items()} for state, counter in transitions.items()}

def generate_from_chart(chart, state_size, min_words=50):
    def get_starter():
        starters = [s for s in chart.keys() if s[0][0].isupper() and not any(p in s[0] for p in ".!?")]
        return random.choice(starters)
    state = get_starter()
    output = list(state)
    while len(output) < min_words:
        next_probs = chart.get(state)
        if not next_probs:
            state = random.choice(list(chart.keys()))
            next_probs = chart[state]
        next_word = random.choices(list(next_probs.keys()), weights=list(next_probs.values()), k=1)[0]
        if not output[-1].endswith((".", "!", "?")):
            next_word = next_word.lower()
        elif output[-1].endswith((".", "!", "?")):
            next_word = next_word.capitalize()
        output.append(next_word)
        state = tuple(output[-state_size:])
    while not output[-1].endswith(('.', '!', '?')):
        next_probs = chart.get(state)
        if not next_probs:
            state = random.choice(list(chart.keys()))
            next_probs = chart[state]
        next_word = random.choices(list(next_probs.keys()), weights=list(next_probs.values()), k=1)[0]
        if not output[-1].endswith((".", "!", "?")):
            next_word = next_word.lower()
        output.append(next_word)
        state = tuple(output[-state_size:])
    return " ".join(output)


def search(keywords, num=5):
    with DDGS() as ddgs:
        results = ddgs.text(keywords, max_results=num)
        return [res['href'] for res in results if 'href' in res]

def scrape_text(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
            return "" 
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')
        for s in soup(["script", "style", "noscript", "footer"]):
            s.extract()
        text_parts, char_count = [], 0
        for p in soup.find_all(['p', 'h1', 'h2', 'h3']):
            data = p.get_text(strip=True)
            if data and re.search(r'[A-Za-z]{3}', data): 
                cleaned = re.sub(r'[^A-Za-z0-9 ,.\'!?-]', ' ', data)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if len(cleaned.split()) > 3:
                    text_parts.append(cleaned)
                    char_count += len(cleaned)
                    if char_count > 1000: 
                        break
        return ' '.join(text_parts)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def main():
    keywords = input("Enter search query: ")
    urls = search(keywords, num=5)
    if not urls:
        print("No results found.")
        return
    scraped_text = ""
    for u in urls:
        scraped_text += scrape_text(u)
    if not scraped_text.strip():
        print("No text scraped.")
        return
    state_size = int(input("Enter state size (try 1-4): "))
    min_words = int(input("Enter min words to generate: "))
    chart = build_ngram_chart(scraped_text, state_size)
    generated = generate_from_chart(chart, state_size, min_words)
    new_text = replace(generated.split(" "))
    url = "https://api.languagetool.org/v2/check"
    payload = {'text': new_text, 'language': "en-US"}
    try:
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        corrected_text = new_text
        for match in sorted(result['matches'], key=lambda m: m['offset'], reverse=True):
            if match['replacements']:
                replacement = match['replacements'][0]['value']
                start = match['offset']
                end = start + match['length']
                corrected_text = corrected_text[:start] + replacement + corrected_text[end:]
    except Exception as e:
        print(f"Grammar correction failed: {e}")

    final_text = make_coherent(corrected_text)
    print("\nGenerated text:\n", final_text)


if __name__ == "__main__":
    try:
        print("Warming up coherence model...")
        subprocess.run(
            ['ollama', 'run', 'phi3'],
            input="Hello".encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
        print("Model warm-up complete.")
    except Exception as e:
        print("Model warm-up failed:", e)
    main() 
    input("\nPress Enter to exit program\n")
