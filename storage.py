import json
import csv
from typing import List
from pathlib import Path



def save_proxies(proxies: List[str], filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(proxies)))


def save_proxies_json(proxies: List[str], filepath: Path, geo_data: dict = None) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for p in sorted(proxies):
        ip = p.split(':')[0]
        entry = {
            "ip": ip,
            "port": int(p.split(':')[1]),
            "protocol": filepath.stem.split('_')[0]
        }
        if geo_data and ip in geo_data:
            entry.update(geo_data[ip])
        data.append(entry)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def save_proxies_csv(proxies: List[str], filepath: Path, geo_data: dict = None) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ["ip", "port", "protocol"]
        if geo_data:
            header.extend(["country", "countryCode", "city"])
        
        writer.writerow(header)
        protocol = filepath.stem.split('_')[0]
        
        for proxy in sorted(proxies):
            ip, port = proxy.split(':')
            row = [ip, port, protocol]
            if geo_data and ip in geo_data:
                info = geo_data[ip]
                row.extend([info.get('country', ''), info.get('countryCode', ''), info.get('city', '')])
            elif geo_data:
                 row.extend(['', '', ''])
            writer.writerow(row)


def load_proxies(filepath: Path) -> List[str]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:

        return []
