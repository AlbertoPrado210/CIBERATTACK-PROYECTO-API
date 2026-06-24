"""
ml-test.py
Script de prueba local para verificar todos los endpoints de la API.

Uso:
  1. Levanta el servidor:  uvicorn main:app --port 8000
  2. En otra terminal:     python ml-test.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def request(method: str, path: str, body: dict | None = None) -> dict:
    url  = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": json.loads(e.read())}


def sep(title: str):
    print(f"\n{'='*55}\n  {title}\n{'='*55}")


sep("GET /")
print(json.dumps(request("GET", "/"), indent=2))

sep("GET /health")
print(json.dumps(request("GET", "/health"), indent=2))

sep("GET /cyberattack/classes")
resp = request("GET", "/cyberattack/classes")
print(f"n_clases: {resp.get('n_clases')}")
print(f"Primeras 5: {resp.get('categorias', [])[:5]}")

sep("POST /cyberattack/predict — Web Application")
print(json.dumps(request("POST", "/cyberattack/predict", {
    "mitre_technique": "T1190 (Exploit Public-Facing Application)",
    "tools_used":      "Burp Suite, SQLMap",
    "target_type":     "Web Application",
    "source":          "OWASP",
}), indent=2))

sep("POST /cyberattack/predict — Malware")
print(json.dumps(request("POST", "/cyberattack/predict", {
    "mitre_technique": "T1059 (Command and Scripting Interpreter)",
    "tools_used":      "Metasploit, Python",
    "target_type":     "Windows",
    "source":          "MITRE ATT&CK",
}), indent=2))

sep("POST /cyberattack/predict — IoT")
print(json.dumps(request("POST", "/cyberattack/predict", {
    "mitre_technique": "T1040 (Network Sniffing)",
    "tools_used":      "Wireshark, Scapy",
    "target_type":     "IoT Device",
    "source":          "NIST",
}), indent=2))

print("\nTodos los tests completados.")
