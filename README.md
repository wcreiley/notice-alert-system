# Notice Alert system

## Running Locally

### Requirements
- pyenv 2.5.5
- virtualenv 20.30.0
- Python 3.13

### Setup dependencies
- brew install pyenv virtualenv
- pyenv install 3.13.2
- python dependencies
  ```
  virtualenv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

### Setup .env file
- `cp config/dot.env .env`
- Edit `.env` file with OpenAI and Slack credentials and OpenAI model information
  ```
  OPENAI_API_KEY=your_openai_api_key
  SLACK_BOT_TOKEN=your_slack_bot_token
  SLACK_CHANNEL_ID=your_slack_channel_id
  EMBEDDER_LOCATOR="text-embedding-ada-002"
  EMBEDDING_DIMENSION="1536"
  MODEL_LOCATOR="gpt-3.5-turbo"
  MAX_TOKEN="400"
  TEMPERATURE="0.0"  
  ```
  
### Start Application

#### Ingest Service
- `python src/Ingest.py`

#### LLM Engine
- `python src/LlmEngine.py`

#### Alert Service
- `python src/AlertService.py`

#### UI Management
- `streamlit run src/UiMgmt.py --server.port 8501 --server.address 0.0.0.0`