import tls_client
import time
import json
import logging
import concurrent.futures
import random
from datetime import datetime
from collections import Counter
import sys
import os

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Color constants for terminal output
GREY = '\033[90m'
GREEN = '\033[92m'
ORANGE = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BLUE = '\033[94m'
DARK_BLUE = '\033[34m'
YELLOW = '\033[93m'
WHITE = '\033[97m'
RESET = '\033[0m'

def current_timestamp():
    return datetime.now().strftime('[%H:%M:%S]')

def read_config(file_path='input/config.json'):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"Config file {file_path} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}.")
        sys.exit(1)

def read_proxies_from_file(file_path='input/proxy.txt'):
    try:
        with open(file_path, 'r') as file:
            return [proxy.strip() for proxy in file.readlines() if proxy.strip()]
    except FileNotFoundError:
        logging.error(f"Proxy file {file_path} not found.")
        return []

def format_proxy(proxy):
    """Format proxy string to tls_client format"""
    if not proxy:
        return None
        
    try:
        if '@' in proxy:
            auth, hostport = proxy.split('@')
            username, password = auth.split(':')
            host, port = hostport.split(':')
            return {
                "http": f"http://{username}:{password}@{host}:{port}",
                "https": f"http://{username}:{password}@{host}:{port}"
            }
        else:
            host, port = proxy.split(':')
            return {
                "http": f"http://{host}:{port}",
                "https": f"http://{host}:{port}"
            }
    except ValueError:
        logging.error(f"Invalid proxy format: {proxy}")
        return None

def get_random_proxy(proxies, use_proxy):
    if not use_proxy or not proxies:
        return None
    return format_proxy(random.choice(proxies))

def create_tls_session(proxy_dict=None):
    # Create a TLS client session with Chrome 120 fingerprint
    session = tls_client.Session(
        client_identifier="chrome_120",
        random_tls_extension_order=True
    )
    
    # Set standard Discord headers
    session.headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://discord.com',
        'referer': 'https://discord.com/channels/@me',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-debug-options': 'bugReporterEnabled',
        'x-discord-locale': 'en-US',
        'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI1MDgzMiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0='
    }
    
    # Set proxy if provided
    if proxy_dict:
        session.proxies = proxy_dict
        
    return session

def make_request(session, method, url, token, **kwargs):
    """Make a request with proper error handling and rate limit handling"""
    session.headers['authorization'] = token
    
    try:
        response = getattr(session, method)(url, **kwargs)
        
        if response.status_code == 429:
            retry_after = response.json().get('retry_after', 5)
            logging.warning(f"Rate limited, waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return make_request(session, method, url, token, **kwargs)
            
        return response
        
    except Exception as e:
        logging.error(f"Request error: {str(e)}")
        raise e

def fetch_guild_ids(token, proxies, use_proxy, retries=5, rate_limit_delay=1):
    proxy_dict = get_random_proxy(proxies, use_proxy)
    session = create_tls_session(proxy_dict)
    
    guild_ids = []
    for attempt in range(retries):
        try:
            response = make_request(session, 'get', 'https://discord.com/api/v9/users/@me/guilds', token)
            
            if response.status_code == 200:
                guilds = response.json()
                guild_ids.extend(guild['id'] for guild in guilds)
                guild_count = len(guilds)
                token_start = token[:10]
                token_end = token[-4:]
                print(f' {current_timestamp()} {GREEN}[SUCCESS]{RESET} {WHITE}Token: {CYAN}{token_start}...{token_end}{RESET} | Guilds: {CYAN}{guild_count}{RESET}')
                return guild_ids
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', rate_limit_delay))
                time.sleep(retry_after)
            elif response.status_code == 401:
                token_start = token[:10]
                token_end = token[-4:]
                print(f' {current_timestamp()} {RED}[FAIL]{RESET} {WHITE}Token: {CYAN}{token_start}...{token_end}{RESET} {RED}[ISSUE]{RESET} Invalid Token')
                return guild_ids
            else:
                logging.warning(f"Unexpected status code: {response.status_code}")
                time.sleep(rate_limit_delay)
        except Exception as e:
            token_start = token[:10]
            token_end = token[-4:]
            print(f' {current_timestamp()} {RED}[FAIL]{RESET} {WHITE}Token: {CYAN}{token_start}...{token_end}{RESET} {RED}[ISSUE]{RESET} Request Error: {str(e)}')
            
            # Try with a different proxy
            if use_proxy and proxies:
                proxy_dict = get_random_proxy(proxies, use_proxy)
                session = create_tls_session(proxy_dict)
            
            time.sleep(rate_limit_delay)

    return guild_ids

def token_generator(file_path='input/tokens.txt'):
    try:
        with open(file_path, 'r') as file:
            for line in file:
                yield line.strip()
    except FileNotFoundError:
        logging.error(f"Token file {file_path} not found.")
        sys.exit(1)

def extract_token(line):
    if ':' in line:
        parts = line.split(':')
        return parts[-1]
    return line

def save_all_guild_ids_to_file(guild_ids, file_path='guilds.txt'):
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(file_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(file_path, 'w') as file:
            for guild_id in guild_ids:
                file.write(f'{guild_id}\n')
        
        print(f' {current_timestamp()} {GREEN}[SUCCESS]{RESET} Saved {len(guild_ids)} guilds to {file_path}')
    except IOError as e:
        logging.error(f"Error writing to file {file_path}: {e}")

def collect_all_guild_ids(file_path, proxies, use_proxy, max_workers=10):
    all_guild_ids = []
    tokens = list(token_generator(file_path))
    total_tokens = len(tokens)
    
    print(f' {current_timestamp()} {CYAN}[INFO]{RESET} Starting to process {total_tokens} tokens with {max_workers} threads')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_token = {
            executor.submit(fetch_guild_ids, extract_token(token), proxies, use_proxy): token
            for token in tokens
        }

        completed = 0
        for future in concurrent.futures.as_completed(future_to_token):
            guild_ids = future.result()
            if guild_ids:
                all_guild_ids.extend(guild_ids)
            
            completed += 1
            if completed % 10 == 0 or completed == total_tokens:
                print(f' {current_timestamp()} {CYAN}[PROGRESS]{RESET} Processed {completed}/{total_tokens} tokens')

    return all_guild_ids

def get_user_input():
    BLUE = '\033[94m'
    RESET = '\033[0m'
    while True:
        try:
            max_workers = int(input(f" {current_timestamp()} {BLUE}[INPUT]{RESET} Please input the amount of threads you want to use: "))
            if max_workers <= 0:
                print(" Thread count must be greater than 0")
                continue
            return max_workers
        except ValueError:
            print(" Please enter a valid number.")

def check_directories():
    # Create necessary directories if they don't exist
    required_dirs = ['input', 'output']
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f" {current_timestamp()} {CYAN}[SETUP]{RESET} Created {directory} directory")
    
    # Check for config file
    if not os.path.exists('input/config.json'):
        # Create default config
        default_config = {
            "proxy": "false",
            "thread_count": 10
        }
        with open('input/config.json', 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f" {current_timestamp()} {CYAN}[SETUP]{RESET} Created default config.json")

def main():
    BLUE = '\033[94m'
    DARK_BLUE = '\033[34m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    ascii_art = f"""
        {DARK_BLUE}▄▄▄▄    ▒█████   ▒█████   ███▄ ▄███▓  ██████ 
        ▓█████▄ ▒██▒  ██▒▒██▒  ██▒▓██▒▀█▀ ██▒▒██    ▒ 
        ▒██▒ ▄██▒██░  ██▒▒██░  ██▒▓██    ▓██░░ ▓██▄   
        ▒██░█▀  ▒██   ██░▒██   ██░▒██    ▒██   ▒   ██▒
        ░▓█  ▀█▓░ ████▓▒░░ ████▓▒░▒██▒   ░██▒▒██████▒▒
        ░▒▓███▀▒░ ▒░▒░▒░ ░ ▒░▒░▒░ ░ ▒░   ░  ░▒ ▒▓▒ ▒ ░
        ▒░▒   ░   ░ ▒ ▒░   ░ ▒ ▒░ ░  ░      ░░ ░▒  ░ ░
        ░    ░ ░ ░ ░ ▒  ░ ░ ░ ▒  ░      ░   ░  ░  ░  
        ░          ░ ░      ░ ░         ░         ░  
            ░                                       
        {RESET}
    """
    print("   " + ascii_art)
    print(f" {current_timestamp()} {BLUE}[INFO]{RESET} Welcome to Booms IDFetcher - TLS Enhanced\n")

    # Check and create necessary directories and files
    check_directories()

    config = read_config()
    use_proxy = config.get('proxy', 'false').lower() == 'true'
    proxies = read_proxies_from_file('input/proxy.txt') if use_proxy else []
    
    if use_proxy and not proxies:
        print(f" {current_timestamp()} {YELLOW}[WARNING]{RESET} Proxy usage is enabled but no proxies found. Running without proxies.")
        use_proxy = False

    max_workers = config.get('thread_count', 10)
    user_max_workers = get_user_input()
    if user_max_workers:
        max_workers = user_max_workers

    all_guild_ids = collect_all_guild_ids(
        'input/tokens.txt',
        proxies,
        use_proxy,
        max_workers=max_workers
    )

    print()

    total_guilds = len(all_guild_ids)
    guild_counter = Counter(all_guild_ids)
    unique_guild_ids = list(guild_counter.keys())
    duplicates_count = total_guilds - len(unique_guild_ids)

    # Create timestamp for output folder
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    output_path = f'output/guilds_{timestamp}.txt'
    save_all_guild_ids_to_file(unique_guild_ids, output_path)

    if duplicates_count == 0:
        print(f" {current_timestamp()} {YELLOW}[RESULTS]{RESET} {WHITE}Fetched {total_guilds} guilds and no dupes were found.{RESET}")
    else:
        print(f" {current_timestamp()} {YELLOW}[RESULTS]{RESET} {WHITE}Fetched {total_guilds} guilds and removed {duplicates_count} duplicates from the list.{RESET}")

if __name__ == "__main__":
    main()
