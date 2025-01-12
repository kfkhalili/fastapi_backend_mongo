# FMP Playground

## Project Setup

1. Install [Poetry](https://python-poetry.org/docs/)

```bash
# mac installation
brew install poetry
```

2. Install dependencies

```bash
poetry install --no-root
```

3. Set Environmental Variables

```bash
touch .env.local
echo "MONGODB_URI=your_connection_string_here" >> .env.local
echo "FMP_API_KEY=your_fmp_api_key_here" >> .env.local
```

3. Populate Database

```bash
poetry run python setup_mongo.py
```

4. Run Backend API

```bash
poetry run uvicorn main:app --reload
```
