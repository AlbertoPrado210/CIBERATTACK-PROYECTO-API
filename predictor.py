"""
predictor.py
Carga los artefactos de ML una sola vez al arrancar el proceso
y expone una funcion predict() que acepta datos crudos del request.

Secuencia de transformacion:
  raw input -> extract_features() -> encode (LabelEncoder por columna)
            -> scale (StandardScaler) -> xgb.predict() -> decode target
"""

import os
import re
import logging
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_BASE_DIR, "models")


def _model_path(filename: str) -> str:
    return os.path.join(_MODELS_DIR, filename)


@lru_cache(maxsize=1)
def _load_artifacts() -> dict:
    """
    Carga todos los artefactos desde disco una unica vez.
    lru_cache garantiza que no se vuelvan a leer en requests subsiguientes.
    """
    logger.info("Cargando artefactos de ML desde %s ...", _MODELS_DIR)

    artifacts = {
        "model":         joblib.load(_model_path("xgb_model.pkl")),
        "scaler":        joblib.load(_model_path("scaler.pkl")),
        "le_target":     joblib.load(_model_path("label_encoder_target.pkl")),
        "feat_encoders": joblib.load(_model_path("feature_encoders.pkl")),
        "feature_names": joblib.load(_model_path("feature_names.pkl")),
    }

    logger.info(
        "Artefactos cargados | Modelo: %s | Clases: %d | Features: %s",
        type(artifacts["model"]).__name__,
        len(artifacts["le_target"].classes_),
        artifacts["feature_names"],
    )
    return artifacts


# Deben coincidir exactamente con los usados en group_top_n() del notebook.

_TOP_TOOLS = {
    "AFL++", "AWS CLI", "Android Studio", "Bettercap", "Binwalk",
    "Browser", "Burp Suite", "ChatGPT", "Docker", "FTK Imager",
    "GitHub Actions", "Ghidra", "Gobuster", "Hydra", "IDA Pro",
    "Kali Linux", "Metasploit", "Mimikatz", "Nessus", "Nmap",
    "OpenSSL", "OWASP ZAP", "PowerShell", "PyTorch", "Python",
    "Radare2", "Scapy", "Shodan", "Splunk", "Wireshark",
    "curl", "kubectl", "sqlmap", "tcpdump", "volatility",
    "Aircrack-ng", "BeEF", "Cobalt Strike", "Empire", "John the Ripper",
    "Nikto", "OpenVAS", "Responder", "SET", "THC Hydra",
    "Wfuzz", "hashcat", "msfconsole", "netcat", "reaver",
}

_TOP_TARGETS = {
    "Android App", "Android Device", "Browser", "Browsers", "Cloud VMs",
    "Developers", "Endpoint", "GitHub Actions", "Infotainment System",
    "Internal Network", "IoT Device", "Linux", "Linux Server",
    "Mobile App", "Network", "OT/ICS Systems", "PLC", "Passenger Vehicle",
    "Satellite", "Smart Devices", "Web Application", "Web apps",
    "Windows", "Windows Host", "Windows Server", "Windows Workstation",
    "Workstation", "Workstations", "macOS", "routers",
}

_TOP_SOURCES = {
    "AWS Docs", "Anthropic", "ChatGPT (OpenAI)", "Custom",
    "Educational", "Educational Simulation", "GitHub", "Google",
    "Hugging Face", "IEEE", "MITRE ATT&CK", "Microsoft Docs",
    "NIST", "OWASP", "OpenAI", "PortSwigger", "Rapid7",
    "Research Paper", "SANS", "Shodan Docs", "Tenable",
    "USENIX", "arXiv", "cve.mitre.org", "exploit-db.com",
    "kali.org", "owasp.org", "packetstormsecurity.com",
    "rapid7.com", "snort.org",
}

_MITRE_RE = re.compile(r"T\d{4}")


def _extract_features(
    mitre_technique: str,
    tools_used: str,
    target_type: str,
    source: str,
) -> pd.DataFrame:
    """
    Replica exactamente el feature engineering del notebook de entrenamiento.
    Devuelve un DataFrame con una fila y las 4 columnas esperadas por el modelo.
    """
    # feat_mitre: primer codigo T-XXXX del texto
    match = _MITRE_RE.search(mitre_technique)
    feat_mitre = match.group() if match else "Unknown"

    # feat_tool / feat_target / feat_source:
    #   primer valor del campo multi-valor, agrupado en Top-N o "Other"
    def _first_or_other(text: str, top_set: set) -> str:
        first = text.split(",")[0].strip()
        return first if first in top_set else "Other"

    feat_tool   = _first_or_other(tools_used,  _TOP_TOOLS)
    feat_target = _first_or_other(target_type, _TOP_TARGETS)
    feat_source = _first_or_other(source,      _TOP_SOURCES)

    return pd.DataFrame(
        [[feat_mitre, feat_tool, feat_target, feat_source]],
        columns=["feat_mitre", "feat_tool", "feat_target", "feat_source"],
    )


def predict(
    mitre_technique: str,
    tools_used: str,
    target_type: str,
    source: str,
) -> dict:
    """
    Recibe los cuatro campos de texto en crudo, aplica el pipeline completo
    y devuelve la categoria predicha junto con las probabilidades top-3.

    Returns
    -------
    {
        "categoria": str,
        "confianza": float,
        "top3": [{"categoria": str, "probabilidad": float}, ...]
    }
    """
    art = _load_artifacts()

    # Extraccion de features
    df_raw = _extract_features(mitre_technique, tools_used, target_type, source)

    # Label Encoding por columna con fallback a "Other" para valores desconocidos
    df_enc = df_raw.copy()
    for col, enc in art["feat_encoders"].items():
        raw_val = df_enc[col].iloc[0]
        known   = set(enc.classes_)
        safe    = raw_val if raw_val in known else "Other"
        df_enc[col] = enc.transform([safe])

    # Garantizar orden de columnas exacto del entrenamiento
    df_enc = df_enc[art["feature_names"]]

    # Escalado (StandardScaler ajustado en entrenamiento)
    X_scaled = art["scaler"].transform(df_enc.values.astype(float))

    # Prediccion con probabilidades
    proba         = art["model"].predict_proba(X_scaled)[0]
    predicted_idx = int(np.argmax(proba))
    predicted_lbl = art["le_target"].classes_[predicted_idx]

    # Top-3 categorias mas probables
    top3_idx = np.argsort(proba)[::-1][:3]
    top3 = [
        {
            "categoria":    art["le_target"].classes_[i],
            "probabilidad": round(float(proba[i]), 4),
        }
        for i in top3_idx
    ]

    return {
        "categoria": predicted_lbl,
        "confianza": round(float(proba[predicted_idx]), 4),
        "top3":      top3,
    }
