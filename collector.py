import re
import socket
import time
import urllib.request

# 1. Пять популярных GitHub-списков VLESS-ключей (raw-ссылки)
#    Это обычные текстовые файлы, которые GitHub отдаёт напрямую.
URLS = [
    # 0xRadikal — «топ-100» проверенных конфигов (там есть и VLESS)
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    # barry-far — отдельный файл только с VLESS
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    # SoliSpirit — отдельный файл только с VLESS
    "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vless.txt",
    # ALIILAPRO — большой общий список (берём только строки, начинающиеся с vless://)
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/server.txt",
    # kort0881 — ежедневный список для России (тоже фильтруем по vless://)
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
]

# 2. Регулярка, которая вытаскивает IP (или домен) и порт из ключа VLESS.
#    Пример ключа: vless://uuid@1.2.3.4:443?...
PATTERN = re.compile(r"vless://[^@]+@([^:]+):(\d+)")

def download(url: str) -> str:
    """Скачивает текст по ссылке. Если не получилось — возвращает пустую строку."""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Не удалось скачать {url}: {e}")
        return ""

def check_server(host: str, port: int) -> float | None:
    """
    Пытается открыть TCP-соединение с host:port.
    Возвращает время в секундах, если сервер ответил, иначе None.
    """
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=2.0):
            return time.perf_counter() - start
    except Exception:
        return None

def main() -> None:
    # Шаг 1: собираем все строки, которые начинаются с vless://
    all_keys: list[str] = []
    for url in URLS:
        text = download(url)
        # Разбиваем на строки, убираем пробелы, оставляем только vless://
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("vless://"):
                all_keys.append(line)

    print(f"Всего найдено VLESS-ключей: {len(all_keys)}")

    # Шаг 2: проверяем каждый ключ и запоминаем скорость
    results: list[tuple[float, str]] = []   # (секунды, ключ)
    for key in all_keys:
        match = PATTERN.search(key)
        if not match:
            continue                         # если формат не распознан — пропускаем

        host, port_str = match.groups()
        try:
            port = int(port_str)
        except ValueError:
            continue

        delay = check_server(host, port)
        if delay is not None:                # сервер ответил
            results.append((delay, key))

    print(f"Рабочих ключей: {len(results)}")

    # Шаг 3: сортируем по времени ответа (сначала самые быстрые) и берём 15
    results.sort(key=lambda x: x[0])
    top15 = results[:15]

    # Шаг 4: записываем в keys.txt
    with open("keys.txt", "w", encoding="utf-8") as f:
        for delay, key in top15:
            f.write(key + "\n")
            print(f"{delay:.3f} сек — {key[:60]}...")   # показываем начало ключа

    print("Готово! 15 самых быстрых ключей сохранены в keys.txt")

if __name__ == "__main__":
    main()
