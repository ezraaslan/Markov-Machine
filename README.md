# Markov-Machine
This is my first try at a computationally efficient text-generation algorithm. Contrary to LLMs, this lightweight program uses Markov Chains and other rules of probability to analyze relationships between words in inputted text. It uses this to reform sentences and paragraphs in order to generate a new format from the original corpus. What's so revolutionary is that my program runs in constant time by analyzing the relationships between the words (O(1)) but an AI model runs in exponential time by iterating over each word and checking it in a token dictionary against the others (O(n^2)).

DEMO INSTRUCTIONS
Run the program interactively:

Go to the releases page and click on the Markov_Generator.exe to run. It takes a minute to load once you run it in the terminal -- don't worry, it should still work.
The Runtime Warning about ddgs() is NOT AN ERROR -- is just appears on the screen with the version of the search library I have implemented. For the demo, type in a simple question ('What is a capybara?') and enter a state size like 3. Set the min word count to something like 20 or 30 (it can support more words, it just might take longer to generate). NOTE: this version of the .exe (v1.0.0) does not include the recent changes I have made by implementing an AI model to parse the text because it would require the user to download the model separately, so just know that the text might not be the most sensical ouput you have ever seen :). However, the current version I have (and will update soon) is much better at generating text.

v2.0.0 UPDATE: This release DOES INCLUDE a coherence model, so the output is very good! However, to run the current program to fullest of its capabilities you will need to have Ollama installed os you can connect to one of its models.
