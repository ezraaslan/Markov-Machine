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
from concurrent.futures import ThreadPoolExecutor
import time
import atexit
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

def tkinter():
    root = tk.Tk()
    root.title("Next-Gen Text Generator")
    root.geometry("800x600")

    tk.Label(root, text="Enter search query:").pack(anchor="w", padx=10, pady=(10, 0))
    keywords_text = tk.Text(root, height=4, width=80)
    keywords_text.pack(padx=10, pady=(0, 10))

    params_frame = tk.Frame(root)
    params_frame.pack(padx=10, pady=5, fill="x")

    tk.Label(params_frame, text="State size:").grid(row=0, column=0, sticky="w")
    state_size_spin = tk.Spinbox(params_frame, from_=1, to=4, width=5)
    state_size_spin.grid(row=1, column=0, sticky="w", padx=(0, 20))

    tk.Label(params_frame, text="Min words to generate:").grid(row=0, column=1, sticky="w")
    min_words_spin = tk.Spinbox(params_frame, from_=10, to=500, increment=10, width=7)
    min_words_spin.grid(row=1, column=1, sticky="w", padx=(0, 20))

    tk.Label(params_frame, text="Model:").grid(row=0, column=2, sticky="w")
    model_combo = ttk.Combobox(params_frame, values=["phi3", "phi3-mini"], state="readonly", width=10)
    model_combo.current(0) 
    model_combo.grid(row=1, column=2, sticky="w")

    output_box = scrolledtext.ScrolledText(root, height=20, width=95)
    output_box.pack(padx=10, pady=10, fill="both", expand=True)

    def run_generation():
        keywords = keywords_text.get("1.0", "end").strip()
        if not keywords:
            messagebox.showerror("Input Error", "Please enter a search query.")
            return
        try:
            state_size = int(state_size_spin.get())
            min_words = int(min_words_spin.get())
        except ValueError:
            messagebox.showerror("Input Error", "State size and min words must be numbers.")
            return
        model = model_combo.get()

        output_box.delete("1.0", "end")
        output_box.insert("end", "Starting text generation...\n")

       
        def task():
            urls = search(keywords, num=5)
            if not urls:
                messagebox.showerror("Input Error", "No search results found. Please regenerate.")
                return
            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(scrape_text, urls))

            scraped_text = " ".join(filter(None, results))

            if not scraped_text.strip():
                messagebox.showerror("Input Error", "No text scraped.")
                return
            



            chart = build_ngram_chart(scraped_text, state_size)
            generated = generate_from_chart(chart, state_size, min_words)
            new_text = replace(generated.split(" "))

            final_text = make_coherent(new_text, model)


            final_text = f"Keywords: {keywords}\nState Size: {state_size}\nMin Words: {min_words}\nModel: {model}\n\nGenerated text:\n{final_text}"


            def update_output():
                output_box.insert("end", final_text + "\n")
            root.after(0, update_output)

        threading.Thread(target=task).start()

    generate_button = tk.Button(root, text="Generate", command=run_generation)
    generate_button.pack(pady=5)

    root.mainloop()
class OllamaServer:
    def __init__(self):
        self.process = None

    def start(self):
        if self.process is not None:
            return True 

        messagebox.showinfo("Update", "Starting Ollama server...")
        self.process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for _ in range(20):
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=0.5)
                if r.status_code == 200:
                    messagebox.showinfo("Update", "Ollama server is up and running.")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(0.5)

        messagebox.showinfo("Update", "Ollama server did not start in time.")
        return False

    def stop(self):
        if self.process:
            messagebox.showinfo("Update", "Stopping Ollama server...")
            self.process.terminate()
            self.process = None

ollama = OllamaServer()

atexit.register(ollama.stop)

if not ollama.start():
    messagebox.showinfo("Update", "Failed to start Ollama server. Exiting program.")
    exit(1)

def make_coherent(text, model="phi3"):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": f"Fix awkward grammar and out-of-place synonyms in the following text, without changing the meaning or word count. Make it sound human-written, not AI written. Don't use first person. Output only the corrected text, without any extra commentary or labels:\n\n{text}",
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        response_text = resp.json()["response"].strip()
        lines = [line.strip() for line in response_text.splitlines() if line.strip()]
        return lines[-1] if lines else response_text
    except Exception as e:
        messagebox.showinfo("Update", "Coherence model failed.")
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

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_text(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
            return "" 

        soup = BeautifulSoup(response.text, 'lxml')

        for s in soup(["script", "style", "noscript", "footer"]):
            s.extract()

        text_parts = []
        char_count = 0

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

    except Exception:
        return ""

def main():
    tkinter()
    

if __name__ == "__main__":
    main()
