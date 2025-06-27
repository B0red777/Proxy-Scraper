import requests
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import ssl

RED = "\033[91m"
RESET = "\033[0m"

GITHUB_RAW_LINKS = {
    "http": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/master/proxies/http.txt",
    ],
    "socks4": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/master/proxies/socks4.txt",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/master/proxies/socks5.txt",
    ],
}

PROXY_SITES = [
    "https://www.sslproxies.org/",
    "https://free-proxy-list.net/",
]

def fetch_github_proxies():
    proxies = {"http": set(), "socks4": set(), "socks5": set()}
    for proxy_type, urls in GITHUB_RAW_LINKS.items():
        for url in tqdm(
            urls,
            desc=f"Initializing {proxy_type} proxies",
            colour='magenta',
            bar_format='{l_bar}{bar}| Elapsed: {elapsed_s}s'
        ):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                for line in r.text.splitlines():
                    line = line.strip()
                    if line and ":" in line:
                        proxies[proxy_type].add(line)
            except Exception:
                tqdm.write(f"{RED}An error occurred fetching {url}{RESET}")
    return proxies

def scrape_proxy_sites():
    proxies = set()
    for url in PROXY_SITES:
        domain = urlparse(url).netloc
        with tqdm(
            total=1,
            desc=f"Scraping {domain}",
            colour='magenta',
            bar_format='{l_bar}{bar}| Elapsed: {elapsed_s}s'
        ) as pbar:
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                table = soup.find("table", attrs={"id": "proxylisttable"})
                if not table:
                    tqdm.write(f"{RED}An error occurred: No proxy table found on {domain}{RESET}")
                    continue
                for row in table.tbody.find_all("tr"):
                    cols = row.find_all("td")
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    proxy = f"{ip}:{port}"
                    proxies.add(proxy)
            except Exception:
                tqdm.write(f"{RED}An error occurred scraping {domain}{RESET}")
            pbar.update(1)
    return proxies

def check_http_proxy(proxy, timeout=7):
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    test_url = "http://httpbin.org/ip"
    try:
        r = requests.get(test_url, proxies=proxies, timeout=timeout)
        if r.status_code == 200:
            return True
    except Exception:
        return False
    return False

def check_socks_proxy(proxy, socks_version, timeout=7):
    import socket
    import socks

    ip, port = proxy.split(":")
    port = int(port)

    sock = socks.socksocket()
    if socks_version == 4:
        sock.set_proxy(socks.SOCKS4, ip, port)
    elif socks_version == 5:
        sock.set_proxy(socks.SOCKS5, ip, port)
    else:
        return False

    sock.settimeout(timeout)
    try:
        sock.connect(("www.google.com", 443))
        sock.close()
        return True
    except Exception:
        return False

def main():
    while True:
        concurrency_input = input("ccw amount (default 150): ").strip()
        if concurrency_input == "":
            max_workers = 150
            break
        elif concurrency_input.isdigit() and int(concurrency_input) > 0:
            max_workers = int(concurrency_input)
            break
        else:
            print("Please enter a valid positive integer or press Enter for default.")

    github_proxies = fetch_github_proxies()
    print()
    site_proxies = scrape_proxy_sites()

    all_http_proxies = github_proxies["http"].union(site_proxies)
    socks4_proxies = github_proxies["socks4"]
    socks5_proxies = github_proxies["socks5"]

    with open("http.txt", "w") as f:
        for proxy in sorted(all_http_proxies):
            f.write(proxy + "\n")
    with open("socks4.txt", "w") as f:
        for proxy in sorted(socks4_proxies):
            f.write(proxy + "\n")
    with open("socks5.txt", "w") as f:
        for proxy in sorted(socks5_proxies):
            f.write(proxy + "\n")

    all_proxies = all_http_proxies.union(socks4_proxies).union(socks5_proxies)
    with open("all.txt", "w") as f:
        for proxy in sorted(all_proxies):
            f.write(proxy + "\n")

    print("\n")
    print("╭─────────────╮")
    print(f"│ {len(all_http_proxies):<3} HTTP  │")
    print(f"│ {len(socks4_proxies):<3} SOCKS4 │")
    print(f"│ {len(socks5_proxies):<3} SOCKS5 │")
    print(f"│ {len(all_proxies):<3} TOTAL │")
    print("╰─────────────╯")
    print("\n")

    check_input = input("Check proxies now? (y/n): ").strip().lower()
    if check_input != "y":
        print("Exiting...")
        return

    with open("all.txt", "r") as f:
        proxies_to_check = [line.strip() for line in f if line.strip()]

    valid_http = []
    valid_socks4 = []
    valid_socks5 = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        with tqdm(total=len(proxies_to_check), desc="Checking proxies", colour="magenta", bar_format='{l_bar}{bar}| Elapsed: {elapsed_s}s') as pbar:
            for proxy in proxies_to_check:
                if proxy in all_http_proxies:
                    futures[executor.submit(check_http_proxy, proxy)] = (proxy, "http")
                elif proxy in socks4_proxies:
                    futures[executor.submit(check_socks_proxy, proxy, 4)] = (proxy, "socks4")
                elif proxy in socks5_proxies:
                    futures[executor.submit(check_socks_proxy, proxy, 5)] = (proxy, "socks5")
                else:
                    futures[executor.submit(check_http_proxy, proxy)] = (proxy, "http")

            for future in as_completed(futures):
                proxy, ptype = futures[future]
                try:
                    valid = future.result()
                    if valid:
                        if ptype == "http":
                            valid_http.append(proxy)
                        elif ptype == "socks4":
                            valid_socks4.append(proxy)
                        elif ptype == "socks5":
                            valid_socks5.append(proxy)
                except Exception:
                    pass
                pbar.update(1)

    with open("valid_http.txt", "w") as f:
        for proxy in sorted(valid_http):
            f.write(proxy + "\n")
    with open("valid_socks4.txt", "w") as f:
        for proxy in sorted(valid_socks4):
            f.write(proxy + "\n")
    with open("valid_socks5.txt", "w") as f:
        for proxy in sorted(valid_socks5):
            f.write(proxy + "\n")

    print("\nValid proxy counts:")
    print("╭─────────────╮")
    print(f"│ {len(valid_http):<3} HTTP    │")
    print(f"│ {len(valid_socks4):<3} SOCKS4  │")
    print(f"│ {len(valid_socks5):<3} SOCKS5  │")
    print("╰─────────────╯")
    print("\n")

if __name__ == "__main__":
    main()
