import re
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# Пять популярных GitHub-списков VLESS-ключей
URLS = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vless.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/server.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
]

# Регулярка: вытаскивает адрес и порт из ключа vless://uuid@host:port?...
PATTERN = re.compile(r"vless://[^@]+@([^:]+):(\d+)")

MAX_KEYS        = 200    # сколько уникальных ключей берём в проверку
MAX_WORKERS     = 50     # потоков одновременно
SOCKET_TIMEOUT  = 1.5    # таймаут на один ключ, сек
DOWNLOAD_TIMEOUT = 5     # таймаут на скачивание одного списка, сек
TOP_N           = 15     # сколько лучших сохранить


def download(url: str) -> str:
    """Скачивает один список. При ошибке возвращает пустую строку."""
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Не удалось скачать {url}: {e}")
        return ""


def check_server(host: str, port: int):
    """Пробует TCP-соединение. Возвращает время в секундах или None."""
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT):
            return time.perf_counter() - start
    except Exception:
        return None


def main() -> None:
    started = time.time()

    # 1. Параллельно скачиваем все 5 списков (максимум ~5 сек)
    texts = []
    with ThreadPoolExecutor(max_workers=len(URLS)) as ex:
        for fut in as_completed([ex.submit(download, u) for u in URLS]):
            texts.append(fut.result())

    # 2. Собираем первые 200 УНИКАЛЬНЫХ VLESS-ключей
    unique_keys = []
    seen = set()
    for text in texts:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("vless://"):
                continue
            if line in seen:
                continue
            seen.add(line)
            unique_keys.append(line)
            if len(unique_keys) >= MAX_KEYS:
                break
        if len(unique_keys) >= MAX_KEYS:
            break

    print(f"Отобрано уникальных VLESS-ключей: {len(unique_keys)}")

    # 3. Достаём из каждого ключа адрес и порт
    to_check = []
    for key in unique_keys:
        m = PATTERN.search(key)
        if not m:
            continue
        host, port_str = m.groups()
        try:
            port = int(port_str)
        except ValueError:
            continue
        to_check.append((host, port, key))

    # 4. Проверяем в 50 потоков (максимум ~6 сек: 200/50 * 1.5)
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_server, h, p): k for h, p, k in to_check}
        for fut in as_completed(futures):
            delay = fut.result()
            if delay is not None:
                results.append((delay, futures[fut]))

    print(f"Рабочих ключей: {len(results)}")

    # 5. Сортируем по скорости и берём 15 лучших
    results.sort(key=lambda x: x[0])
    top15 = results[:TOP_N]

    with open("keys.txt", "w", encoding="utf-8") as f:
        for delay, key in top15:
            f.write(key + "\n")
            print(f"{delay:.3f} сек — {key[:60]}...")

    print(f"Готово за {time.time() - started:.1f} сек. Сохранено {len(top15)} ключей в keys.txt.")


if __name__ == "__main__":
    main()
