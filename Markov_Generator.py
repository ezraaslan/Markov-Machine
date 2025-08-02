# import random

# def build_model(source, state_size):
#     words = source.split()
#     model = {}
#     for i in range(state_size, len(words)):
#         key = ' '.join(words[i - state_size:i])
#         model.setdefault(key, []).append(words[i])
#     return model

# def generate(model, state_size, max_words):
#     def get_new_starter():
#         starters = [s.split(' ')[0] for s in model.keys()
#                     if s[0].isupper() and not any(p in s for p in ".!?")]
#         return random.choice(starters)

#     def get_random_word():
#         return random.choice([w for words in model.values() for w in words])

#     def get_enders():
#         return [w for words in model.values() for w in words
#                 if w.endswith(('.', '!', '?'))]

#     enders = get_enders()
#     text = [get_new_starter()] 
#     i = 1
#     while i < max_words:
#         key = ' '.join(text[-state_size:]) if len(text) >= state_size else ' '.join(text)

#         current_word = text[-1]
#         if key not in model:
#             next_word = get_random_word()
#             if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                 if enders:
#                     next_word = random.choice(enders)
#                 else:
#                     next_word += "."
#                 text.append(next_word)
#             elif current_word.endswith(('.', '!', '?')):
#                 next_word = get_new_starter()
#                 if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                     if enders:
#                         next_word = random.choice(enders)
#                     else:
#                         next_word += "."
#             text.append(next_word)
#         elif current_word.endswith(('.', '!', '?')):
#             next_word = get_new_starter()
#             if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                 if enders:
#                     next_word = random.choice(enders)
#                 else:
#                     next_word += "."
#                 text.append(next_word)
#             elif current_word.endswith(('.', '!', '?')):
#                 next_word = get_new_starter()
#                 if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                     if enders:
#                         next_word = random.choice(enders)
#                     else:
#                         next_word += "."
#             text.append(next_word)
#         else:
#             next_word = random.choice(model[key])
#             if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                 if enders:
#                     next_word = random.choice(enders)
#                 else:
#                     next_word += "."
#                 text.append(next_word)
#             elif current_word.endswith(('.', '!', '?')):
#                 next_word = get_new_starter()
#                 if i == max_words - 1 and not next_word.endswith(('.', '!', '?')):
#                     if enders:
#                         next_word = random.choice(enders)
#                     else:
#                         next_word += "."
#             text.append(next_word)
#         i += 1

#     return ' '.join(text)

# def main():
#     corpus = input("Enter text here (more repetitive/longer texts lead to more variety): ")
#     size = int(input("Enter state size (try 2 or 3): "))
#     max_words = len(corpus.split(' '))

#     model = build_model(corpus, size)
#     generated = generate(model, size, max_words)

#     print("Generated text:\n" + generated)

# if __name__ == "__main__":
#     main()






from collections import defaultdict, Counter
import random
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import wordnet
import urllib.parse

def pluralize(og, new):
    if og == "is":
        return new
    if og.isupper():
        new = new.capitalize()
    if og.endswith("ed"):
        new += "ed"
    if og.endswith("y") and not og.endswith(("ay","ey","iy","oy","uy")):
        return new + "ies"
    elif og.endswith("s"):
        return new + "es"
    return new


def get_synonym(word, pos=None):
    synonyms = []
    for syn in wordnet.synsets(word, pos=pos):
        for lemma in syn.lemmas():
            name = lemma.name().replace('_', ' ')
            if name.lower() != word.lower():
                synonyms.append(name)
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
    for word, tag in tagged:
        if not word:
            continue
        wn_pos = get_pos(tag)
        if wn_pos in [wordnet.NOUN, wordnet.VERB, wordnet.ADJ]:
            if random.random() < 0.5:
                word = get_synonym(word, wn_pos)
        new_words.append(word)
    
    return ' '.join(new_words) if new_words else ' '.join(words)


def build_ngram_chart(corpus, state_size=2):
    words = corpus.split()
    transitions = defaultdict(Counter)
    for i in range(len(words) - state_size):
        state = tuple(words[i:i + state_size])
        next_word = words[i + state_size]
        transitions[state][next_word] += 1
    return {state: {w: c / sum(counter.values()) for w, c in counter.items()}
            for state, counter in transitions.items()}


def generate_from_chart(chart, state_size, min_words=50):
    def get_starter():
        starters = [s for s in chart.keys()
                    if s[0][0].isupper() and not any(p in s[0] for p in ".!?")]
        return random.choice(starters)

    state = get_starter()
    output = list(state)

    while len(output) < min_words:
        next_probs = chart.get(state)
        if not next_probs:
            state = random.choice(list(chart.keys()))
            next_probs = chart[state]
        next_word = random.choices(list(next_probs.keys()), weights=list(next_probs.values()), k=1)[0]
        output.append(next_word)
        state = tuple(output[-state_size:])

    while not output[-1].endswith(('.', '!', '?')):
        next_probs = chart.get(state) or random.choice(list(chart.values()))
        next_word = random.choice(list(next_probs.keys()))
        output.append(next_word)
        state = tuple(output[-state_size:])

    return " ".join(output)


def search(keywords, num=5):
    url = "https://duckduckgo.com/html/"
    params = {"q": keywords}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for a in soup.select("a.result__a")[:num]:
        link = a.get("href")

        if link.startswith("//"):
            link = "https:" + link

        if "uddg=" in link:
            parsed = urllib.parse.urlparse(link)
            query = urllib.parse.parse_qs(parsed.query)
            if "uddg" in query:
                link = urllib.parse.unquote(query["uddg"][0])

        results.append(link)
    return results


def scrape_text(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
            return "" 

        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'lxml')

        for s in soup(["script", "style", "noscript"]):
            s.extract()

        text_parts, char_count = [], 0
        for p in soup.find_all(['p', 'h1', 'h2', 'h3']):
            data = p.get_text(strip=True)
            if data:
                text_parts.append(data)
                char_count += len(data)
                if char_count > 1000: 
                    break

        return ' '.join(text_parts)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""



def main():
    keywords = input("Enter search query: ")
    urls = search(keywords, num=5)
    print(urls)
    if not urls:
        print("No results found.")
        return
    scraped_text = ""
    for i in range(len(urls)):
        scraped_text += scrape_text(urls[i])
    if not scraped_text.strip():
        print("No text scraped.")
        return

    state_size = int(input("Enter state size (try 1-4): "))
    min_words = int(input("Enter min words to generate: "))

    chart = build_ngram_chart(scraped_text, state_size)
    generated = generate_from_chart(chart, state_size, min_words)
    new_text = replace(generated.split(" "))
    print("\n--- Generated Text ---\n", new_text)


if __name__ == "__main__":
    main()
