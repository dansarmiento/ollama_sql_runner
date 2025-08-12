# Data-LLM (Ollama SQL Interface)

Data-LLM is a Streamlit application that uses a large language model (LLM) to translate natural language questions into SQL queries for a PostgreSQL database. It's designed to be a simple, read-only interface for data exploration.

## Security First

**IMPORTANT**: This application interacts with an Ollama server, which has had several security vulnerabilities in versions prior to `0.1.47`. Before you begin, ensure your Ollama server is updated to the latest version to mitigate risks such as:

- **CVE-2024-39722, CVE-2024-39719**: File Disclosure
- **CVE-2024-37032**: Path Traversal
- **CVE-2024-45436**: Zip Extraction

This application includes a startup check and will refuse to run if it detects an Ollama version older than `0.1.46`. **Updating your Ollama server is the only way to fully resolve these vulnerabilities.**

For enhanced security, it is also highly recommended to:
- Use the `ALLOWED_OLLAMA_MODELS` environment variable to restrict which models can be used.
- Run the Ollama server in a trusted, isolated environment.
- Never expose the Ollama API or this application to the public internet without proper authentication and security measures.

## Prerequisites

Before you install Data-LLM, make sure you have the following installed and configured:

- **Python 3.10+**
- **PostgreSQL**: A running instance that is network-accessible from where you'll run this application.
- **Ollama**: Installed and running locally or on a trusted server.
  - Download from [ollama.com/download](https://ollama.com/download).
  - After installation, pull a model to get started:
    ```bash
    ollama pull llama3.2:latest
    ```

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your_repo_or_local_folder_prepared>
    cd data-llm
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # On macOS/Linux
    source .venv/bin/activate
    # On Windows
    .venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Configuration is managed via environment variables. You can set them directly in your shell or use a `.env` file for convenience.

1.  **Create a `.env` file:**
    Copy the provided example file to create your own configuration file.
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the `.env` file in a text editor and fill in the values for your environment. Refer to the comments in the `.env.example` file for a detailed explanation of each variable.

    Key variables to configure:
    - `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`: Your PostgreSQL connection details.
    - `OLLAMA_BASE_URL`: The URL for your Ollama server.
    - `OLLAMA_MODEL`: The Ollama model you want to use (e.g., `llama3.2:latest`).
    - `ALLOWED_OLLAMA_MODELS`: A comma-separated list of trusted models to enhance security.

## Running the Application

Once you have configured your `.env` file, you can start the Streamlit application:

```bash
streamlit run app.py
```

The application will be available at the local URL provided by Streamlit (usually `http://localhost:8501`).

## Features

- **Natural Language to SQL**: Ask for data in plain English and get SQL queries in return.
- **Read-Only Protection**: The application is designed to only execute `SELECT` statements. It blocks `INSERT`, `UPDATE`, `DELETE`, and other write operations.
- **Automatic LIMIT Enforcement**: If a generated query doesn't have a `LIMIT`, the application automatically adds one based on `DEFAULT_ROW_LIMIT` to prevent overly large results.
- **Schema Awareness**: The LLM is provided with a summarized version of your database schema to improve the accuracy of the generated SQL.
- **Security Measures**: Includes checks for outdated Ollama versions, restrictions on allowed models, and validation of configuration inputs.
