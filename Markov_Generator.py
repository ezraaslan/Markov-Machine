import customtkinter as ctk
import tkinter.messagebox as messagebox
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
import threading
import ctypes
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import wordnet
from nltk.wsd import lesk
import random
import re
import time
import atexit
import subprocess
from collections import defaultdict, Counter
from duckduckgo_search import DDGS

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

status_label = None

def update_status(text):
    if status_label:
        status_label.after(0, lambda: status_label.configure(text=text))

class OllamaServer:
    def __init__(self):
        self.process = None

    def start(self):
        if self.process is not None:
            return True
        update_status("Starting Ollama server...")
        self.process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(20):
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=0.5)
                if r.status_code == 200:
                    update_status("Ollama server is up and running.")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(0.5)
        update_status("Ollama server did not start in time.")
        return False

    def stop(self):
        if self.process:
            update_status("Stopping Ollama server...")
            self.process.terminate()
            self.process = None

ollama = OllamaServer()
atexit.register(ollama.stop)

def make_coherent(text, model="phi3"):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": f"Fix awkward grammar and out-of-place synonyms in the following text without changing its meaning or word count. Make it sound natural and human-written. Do not include any notes. Do not use first person. Do not use second person. Do not summarize or add commentary. Output only the corrected text:\n\n{text}",
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        response_text = resp.json()["response"].strip()
        lines = [line.strip() for line in response_text.splitlines() if line.strip()]
        return lines[-1] if lines else response_text
    except Exception as e:
        update_status("Coherence model failed.")
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


def tkinter():
    
    global status_label

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Next-Gen Text Generator")
    root.geometry("900x700")
    root.configure(bg="#f0f0f0")


    class ToolTip:
        def __init__(self, widget, text, delay=500):
            self.widget = widget
            self.text = text
            self.delay = delay
            self.tip_window = None
            self.after_id = None

            self.widget.bind("<Enter>", self.schedule)
            self.widget.bind("<Leave>", self.hide_tip)

        def schedule(self, event=None):
            self.unschedule()
            self.after_id = self.widget.after(self.delay, self.show_tip)

        def unschedule(self):
            if self.after_id:
                self.widget.after_cancel(self.after_id)
                self.after_id = None

        def show_tip(self, event=None):
            if self.tip_window:
                return

            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
            y = self.widget.winfo_rooty() + (self.widget.winfo_height() // 2)

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")

            label = tk.Label(
                tw,
                text=self.text,
                background="#333333",
                foreground="white",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 10)
            )
            label.pack(ipadx=6, ipady=3)

        def hide_tip(self, event=None):
            self.unschedule()
            if self.tip_window:
                self.tip_window.destroy()
                self.tip_window = None


    def no(event):
        return "break"

    label_query = ctk.CTkLabel(root, text="Enter search query:", font=("Segoe UI Semilight", 18))
    label_query.pack(padx=100, pady=(10, 0), anchor="center")

    keywords_text = ctk.CTkTextbox(root, height=100, width=800, font=("Segoe UI Semilight", 18))
    keywords_text.pack(padx=10, pady=(0, 10))

    params_frame = ctk.CTkFrame(root)
    params_frame.pack(padx=200, pady=5, fill="x")

    label_state = ctk.CTkLabel(params_frame, text="State size:", font=("Segoe UI Semilight", 18))
    label_state.grid(row=0, column=0, pady=(0, 5), sticky="we")
    ToolTip(label_state, "Number of words in the Markov chain state.")

    state_size_combo = ctk.CTkComboBox(params_frame, values=["2", "3", "4"], width=80, font=("Segoe UI Semilight", 18))
    state_size_combo.grid(row=1, column=0, padx=10)
    state_size_combo.set("2")
    ToolTip(state_size_combo._entry, "Select the number of words per state.")

    label_min_words = ctk.CTkLabel(params_frame, text="Min words to generate:", font=("Segoe UI Semilight", 18))
    label_min_words.grid(row=0, column=1, pady=(0, 5), sticky="we")
    ToolTip(label_min_words, "Minimum number of words to output in generated text.")

    min_words_values = [str(i) for i in range(10, 510, 10)]
    min_words_combo = ctk.CTkComboBox(params_frame, values=min_words_values, width=100, font=("Segoe UI Semilight", 18))
    min_words_combo.grid(row=1, column=1, padx=10)
    min_words_combo.set("50")
    ToolTip(min_words_combo._entry, "Choose minimum output length.")

    label_model = ctk.CTkLabel(params_frame, text="Model:", font=("Segoe UI Semilight", 18))
    label_model.grid(row=0, column=2, pady=(0, 5), sticky="we")
    ToolTip(label_model, "phi3 = larger, more time, better output.\nphi3-mini = smaller, faster, less coherent output.")

    model_combo = ctk.CTkComboBox(params_frame, values=["phi3", "phi3-mini"], width=120, font=("Segoe UI Semilight", 18))
    model_combo.grid(row=1, column=2, padx=10)
    model_combo.set("phi3")
    model_combo._entry.bind("<Key>", no) 
    ToolTip(model_combo._entry, "Select the model for text generation.")

    params_frame.columnconfigure((0, 1, 2), weight=1)

    label_output = ctk.CTkLabel(params_frame, text="", font=("Segoe UI Semilight", 18))
    label_output.grid(row=2, column=1, pady=(20, 0))

    label_output = ctk.CTkLabel(root, text="Generated text:", font=("Segoe UI Semilight", 18))
    label_output.pack(pady=(20, 0))

    output_box = ctk.CTkTextbox(root, height=180, width=700, font=("Segoe UI Semilight", 18), wrap="word")
    output_box.pack(padx=50, pady=10, fill="both", expand=True)

    status_label = ctk.CTkLabel(root, text="", font=("Segoe UI Semilight", 18, "italic"))
    status_label.pack(pady=5)

    generate_button = ctk.CTkButton(root, text="Generate", font=("Segoe UI Semilight", 18, "bold"))
    generate_button.pack(pady=5)

    copy_button = ctk.CTkButton(root, text="Copy text", font=("Segoe UI Semilight", 18, "bold"))
    copy_button.pack(pady=20)

    ToolTip(label_state, "Number of words in the Markov chain state.")
    ToolTip(label_min_words, "Minimum number of words to generate in the output.")
    ToolTip(model_combo, "Select the model for text generation.")
    ToolTip(label_query, "Enter a query to be searched on the DuckDuckGo engine.")

    def run_generation():
        keywords = keywords_text.get("1.0", "end").strip()
        if not keywords:
            messagebox.showerror("Input Error", "Please enter a search query.")
            return
        try:
            state_size = int(state_size_combo.get())
            min_words = int(min_words_combo.get())
        except ValueError:
            messagebox.showerror("Input Error", "State size and min words must be numbers.")
            return
        model = model_combo.get()

        output_box.delete("1.0", "end")
        update_status("Searching for URLs...")
        dots = 0
        loading_job = None

        def animate_dots(text):
            nonlocal dots, loading_job
            dots = (dots + 1) % 4
            update_status(text + "." * dots)
            loading_job = root.after(500, lambda: animate_dots(text))

        def start_loading_animation(text):
            nonlocal dots
            dots = 0
            animate_dots(text)

        def stop_loading_animation():
            nonlocal loading_job
            if loading_job:
                root.after_cancel(loading_job)
                loading_job = None

        def task():
            urls = search(keywords, num=5)
            if not urls:
                root.after(0, lambda: messagebox.showerror("Input Error", "No search results found. Please regenerate."))
                update_status("No search results found.")
                return

            root.after(0, lambda: start_loading_animation(f"Found {len(urls)} URLs. Scraping texts"))

            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(scrape_text, urls))

            scraped_text = " ".join(filter(None, results))

            root.after(0, stop_loading_animation)

            if not scraped_text.strip():
                root.after(0, lambda: messagebox.showerror("Input Error", "No text scraped."))
                update_status("No text scraped from URLs.")
                return

            root.after(0, lambda: start_loading_animation("Building n-gram chart"))
            chart = build_ngram_chart(scraped_text, state_size)
            root.after(0, stop_loading_animation)

            root.after(0, lambda: start_loading_animation("Generating text"))
            generated = generate_from_chart(chart, state_size, min_words)
            root.after(0, stop_loading_animation)

            root.after(0, lambda: start_loading_animation("Replacing synonyms"))
            new_text = replace(generated.split(" "))
            root.after(0, stop_loading_animation)

            root.after(0, lambda: start_loading_animation("Making text coherent with model"))
            final_text = make_coherent(new_text, model)
            root.after(0, stop_loading_animation)

            def update_output():
                output_box.insert("end", final_text + "\n")
                update_status("Generation complete.")

            root.after(0, update_output)
            stop_loading_animation()

        threading.Thread(target=task).start()

    def copy():
        text = output_box.get("1.0", "end").strip()
        if text:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            update_status("Text copied!")
        else:
            messagebox.showwarning("Empty", "No generated text to copy.")

    generate_button.configure(command=run_generation)
    copy_button.configure(command=copy)

    def start_ollama_and_update():
        if not ollama.start():
            root.after(0, lambda: messagebox.showinfo("Update", "Failed to start Ollama server. Exiting now..."))
            root.quit()

    root.after(100, start_ollama_and_update)
    root.mainloop()

def main():
    tkinter()

if __name__ == "__main__":
    main()
