# Markov-Machine
This is my first try at a computationally efficient text-generation algorithm. Contrary to LLMs, this lightweight program uses Markov Chains and other rules of probability to analyze relationships between words in inputted text. It uses this to reform sentences and paragraphs in order to generate a new format from the original corpus. What's so revolutionary is that my program runs in constant time by analyzing the relationships between the words (O(1)) but an AI model runs in exponential time by iterating over each word and checking it in a token dictionary against the others (O(n^2)).

DEMO INSTRUCTIONS
Run the program interactively:

```bash
git clone https://github.com/ezraaslan/markov-machine.git
cd markov-machine
python demo.py
