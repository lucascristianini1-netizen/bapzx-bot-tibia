import json
import os

import requests


class OrderStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self.url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
        self.key = (os.environ.get("SUPABASE_KEY") or "").strip()
        self.table = "pedidos"

    @property
    def remote(self):
        return bool(self.url and self.key)

    def _headers(self):
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def save(self, entry):
        if self.remote:
            payload = {k: v for k, v in entry.items() if v is not None}
            try:
                response = requests.post(
                    f"{self.url}/rest/v1/{self.table}",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )
                if response.status_code not in (200, 201):
                    raise RuntimeError(f"Supabase {response.status_code}: {response.text[:200]}")
                return entry
            except Exception as error:
                print(f"[storage] Supabase falhou, gravando em arquivo: {error}")
        self._append_file(entry)
        return entry

    def _append_file(self, entry):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                orders = json.load(f)
            if not isinstance(orders, list):
                orders = []
        except Exception:
            orders = []
        orders.append(entry)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

    def count(self):
        if self.remote:
            try:
                response = requests.get(
                    f"{self.url}/rest/v1/{self.table}?select=id",
                    headers={**self._headers(), "Prefer": "count=exact", "Range": "0-0"},
                    timeout=15,
                )
                total = response.headers.get("content-range", "").split("/")[-1]
                if total.isdigit():
                    return int(total)
            except Exception as error:
                print(f"[storage] Supabase indisponivel no count: {error}")
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return len(json.load(f))
        except Exception:
            return 0