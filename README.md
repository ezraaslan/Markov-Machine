# Markov-Machine
This is my computationally efficient text-generation algorithm. Contrary to LLMs, this lightweight program uses Markov Chains and other rules of probability to analyze relationships between words in inputted text. It uses this to reform sentences and paragraphs in order to generate a new format from the original corpus. What's so revolutionary is that my program runs in constant time by analyzing the relationships between the words (O(1)) but an AI model runs in exponential time by iterating over each word and checking it in a token dictionary against the others (O(n^2)).

DEMO INSTRUCTIONS
Run the program interactively:

Go to the releases page and click on the Markov_Generator.exe to run. It takes a minute to load once you run it in the terminal -- don't worry, it should still work.
The Runtime Warning about ddgs() is NOT AN ERROR -- is just appears on the screen with the version of the search library I have implemented. For the demo, type in a simple question ('What is a capybara?') and enter a state size like 3. Set the min word count to something like 20 or 30 (it can support more words, it just might take longer to generate).

v2.0.0 UPDATE: This release DOES INCLUDE a coherence model, so the output is very good! However, to run the current program to fullest of its capabilities you will need to have Ollama installed so you can connect to one of its models.

v3.0.0 UPDATE: This version boasts all of the same capabilities as the v2.0.0, except now it renders in a nice-looking window application for users' comfort and convinience. This latest version has fancy new GUI elements, including helpful tooltips that explain the under-the-hood process to users if needed.

v4.0.0 UPDATE: I have finished this project and submitted it to my state's 2025 Congressional App Challenge! At this stage, I consider the algorithm completed because it performs well to my standards and no blatant bugs exist in the code. However, since this was such an interesting project to work on, I expect to return to these files with new knowledge I learn in the future.
