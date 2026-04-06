Change into the repository's directory:
bash
cc:
cd your_repository
Install the required dependencies:

cc:
pip install -r requirements.txt
Update the main.py file with your desired input size, output size, and initial state for the Game class.
Run the training script:

css
cc:
python main.py
This will train the LLM model and save it as saved_model.pt.

To load and use the trained model in another script or project, follow these steps:
a. Initialize an LLM model with the appropriate input and output sizes.

b. Load the saved model's state dictionary:

python 
cc:
llm.load_state_dict(torch.load("./saved_model.pt"))
Now you can use the trained model for making predictions or further fine-tuning.

## Infrastructure pass-likelihood scoring

This repo now includes `scoring.py`, a lightweight implementation of a
weighted **Pass-Likelihood + Land Relevance** model for infrastructure
proposals.

### Run the demo

```bash
python scoring.py
```

### Run tests

```bash
python -m unittest test_scoring.py
```

### Scoring inputs

The model uses these categories:

- procedural stage (0-25)
- sponsor strength (0-10)
- funding clarity (0-15)
- route specificity (0-10)
- need case / demand pull (0-10)
- right-of-way tractability (0-10)
- local-plan alignment (0-8)
- opposition/environmental drag (0-7, subtracted)
- land monetization fit (0-19)

Final formula:

`A + B + C + D + E + F + G + I - H`
