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

def build_ngram_chart(corpus, state_size=2):
    words = corpus.split()
    transitions = defaultdict(Counter)

    
    for i in range(len(words) - state_size):
        state = tuple(words[i:i + state_size])
        next_word = words[i + state_size]
        transitions[state][next_word] += 1

   
    chart = {}
    for state, counter in transitions.items():
        total = sum(counter.values())
        chart[state] = {word: count / total for word, count in counter.items()}

    return chart

def generate_from_chart(chart, state_size, max_words=50):

    def get_starter():
        starters = [s for s in chart.keys() 
            if s[0][0].isupper() and not any(p in s[0] for p in ".!?")]
        return random.choice(starters)
    
    state = get_starter()
    output = list(state)

    for _ in range(max_words - state_size):
        next_probs = chart.get(state)
        if not next_probs:
            break
        words = list(next_probs.keys())
        probs = list(next_probs.values())
        next_word = random.choices(words, weights=probs, k=1)[0]
        output.append(next_word)
        state = tuple(output[-state_size:])

    return " ".join(output)

def main():
    corpus = input("Enter training text: ")
    state_size = int(input("Enter state size (try 1-4): "))
    max_words = int(input("Enter max words to generate: "))

    chart = build_ngram_chart(corpus, state_size)
    generated = generate_from_chart(chart, state_size, max_words)
    print("Generated text:\n" + generated)

if __name__ == "__main__":
    main()
