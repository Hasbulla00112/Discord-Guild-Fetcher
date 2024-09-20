import requests
import time
import json
import logging
import concurrent.futures
import random
from datetime import datetime
from collections import Counter
import sys

import urllib3
import warnings
urllib3.disable_warnings()
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

GREY = '\033[90m'
GREEN = '\033[92m'
ORANGE = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
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

def parse_proxy(proxy):
    if proxy:
        try:
            user_pass, ip_port = proxy.split('@')
            return {
                "http": f"http://{user_pass}@{ip_port}",
                "https": f"https://{user_pass}@{ip_port}"
            }
        except ValueError:
            logging.error(f"Invalid proxy format: {proxy}")
            return None
    return None

def get_random_proxy(proxies, use_proxy):
    if not use_proxy or not proxies:
        return None
    return parse_proxy(random.choice(proxies))

def fetch_guild_ids(token, proxies, session, use_proxy, retries=5, rate_limit_delay=1):
    headers = {'Authorization': token}
    proxy_dict = get_random_proxy(proxies, use_proxy)

    guild_ids = []
    for attempt in range(retries):
        try:
            response = session.get('https://discord.com/api/v9/users/@me/guilds', headers=headers, proxies=proxy_dict, timeout=10)
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
            else:
                time.sleep(rate_limit_delay)
        except requests.exceptions.RequestException as e:
            token_start = token[:10]
            token_end = token[-4:]
            print(f' {current_timestamp()} {RED}[FAIL]{RESET} {WHITE}Token: {CYAN}{token_start}...{token_end}{RESET} {RED}[ISSUE]{RESET} Invalid Proxy')
            logging.error(f' Error fetching guild IDs for token {token[:5]}...: {e}')
            return guild_ids

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
        with open(file_path, 'w') as file:
            for guild_id in guild_ids:
                file.write(f'{guild_id}\n')
    except IOError as e:
        logging.error(f"Error writing to file {file_path}: {e}")

def collect_all_guild_ids(file_path, proxies, use_proxy, max_workers=10):
    all_guild_ids = []
    tokens = token_generator(file_path)

    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_guild_ids, extract_token(line), proxies, session, use_proxy, retries=5, rate_limit_delay=1): line
                for line in tokens
            }

            for future in concurrent.futures.as_completed(futures):
                guild_ids = future.result()
                if guild_ids:
                    all_guild_ids.extend(guild_ids)

    return all_guild_ids

def get_user_input():
    BLUE = '\033[94m'
    RESET = '\033[0m'
    while True:
        try:
            max_workers = int(input(f" {current_timestamp()} {BLUE}[INPUT]{RESET} Please input the amount of threads you want to use: "))
            return max_workers
        except ValueError:
            print(" Please enter a valid number.")

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
    print(f" {current_timestamp()} {BLUE}[INFO]{RESET} Welcome to Booms IDFetcher\n")

    config = read_config()
    proxies = read_proxies_from_file('input/proxy.txt')
    use_proxy = config.get('proxy', 'false').lower() == 'true'

    max_workers = get_user_input()

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

    save_all_guild_ids_to_file(unique_guild_ids, 'guilds.txt')

    if duplicates_count == 0:
        print(f" {current_timestamp()} {YELLOW}[RESULTS]{RESET} {WHITE}Fetched {total_guilds} guilds and no dupes were found.{RESET}")
    else:
        print(f" {current_timestamp()} {YELLOW}[INFO]{RESET} Fetched {total_guilds} and removed {duplicates_count} duplicates from the list.{RESET}")

if __name__ == "__main__":
    main()
