# Notice Alert system

## Running Locally

### Requirements
- pyenv 2.5.5
- virtualenv 20.30.0
- Python 3.13

### Set dependencies
- brew install pyenv virtualenv
- pyenv install 3.13.2
- python dependencies
  - virtualenv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
 
### Start Application

#### Ingest Service
- python src/Ingest.py

#### LLM Engine
- python src/LlmEngine.py
