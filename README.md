# Discord Guild Fetcher

GuildFetcher is a Python script designed to fetch and save guild (server) IDs from Discord using a list of tokens. It supports the use of proxies to avoid rate limiting and improve the success rate of requests. The script performs the following tasks:

## Features

1. **Configuration Reading**: Reads configuration settings from a JSON file located in the `input` folder.
2. **Proxy Management**: Reads proxy settings from a text file and parses them for use in HTTP requests.
3. **Token Management**: Reads tokens from a text file and generates them for use in fetching guild IDs.
4. **Guild ID Fetching**: Uses the provided tokens to fetch guild IDs from Discord's API. It handles rate limiting and retries in case of failures.
5. **Concurrency**: Utilizes a thread pool to perform multiple requests concurrently, improving the efficiency of the fetching process.
6. **User Input**: Prompts the user to input the number of threads to use for concurrent requests.
7. **Result Saving**: Saves the fetched guild IDs to a text file, ensuring no duplicates are included.
8. **Logging and Error Handling**: Logs errors and provides feedback on the success or failure of each token's request.

## Requirements

- Python 3.x
- `requests` library

## Installation

1. Clone the repository or download the script.
2. Install the required Python libraries using pip:
    ```sh
    pip install requests
    ```

## Usage

1. Place your configuration file (`config.json`), proxy file (`proxy.txt`), and token file (`tokens.txt`) in the `input` folder.
2. Run the script:
    ```sh
    python GuildFetcher.py
    ```
3. Follow the on-screen instructions to input the number of threads you want to use.

## Configuration

The `config.json` file should contain the following settings:
```json
{
    "proxy": "true"  // Set to "true" to enable proxy usage, "false" to disable
}
