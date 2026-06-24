# CyberAttack Classifier API

> API REST de clasificación multiclase de ciberataques basada en Machine Learning (XGBoost) con técnicas **MITRE ATT&CK**.

---

## Descripcion

**CyberAttack Classifier API** es un servicio web desarrollado con **FastAPI** que permite clasificar automáticamente el tipo de ciberataque a partir de cuatro indicadores clave:

| Campo | Descripcion |
|---|---|
| `mitre_technique` | Técnica MITRE ATT&CK (ej. `T1190`, `T1078`) |
| `tools_used` | Herramienta(s) utilizadas (ej. `Burp Suite`, `Nmap`) |
| `target_type` | Tipo de objetivo del ataque (ej. `Web Application`, `Windows`) |
| `source` | Fuente de referencia (ej. `OWASP`, `MITRE ATT&CK`) |

El modelo devuelve la **categoría predicha**, su **nivel de confianza** y un **Top-3 de categorías** más probables entre las **28 clases** soportadas.

---

## Tecnologias

| Capa | Tecnologia | Version |
|---|---|---|
| Framework API | FastAPI | 0.115.6 |
| Servidor ASGI | Uvicorn | 0.32.1 |
| Validacion | Pydantic v2 | 2.10.3 |
| Modelo ML | XGBoost | 2.1.3 |
| Preprocesado | scikit-learn | 1.5.2 |
| Datos | Pandas / NumPy | 2.2.3 / 1.26.4 |
| Serializacion | Joblib | 1.4.2 |
| Contenerizacion | Docker | — |
| Runtime | Python | 3.11 |

---

## Arquitectura del proyecto

```
proyecto-api/
├── main.py               # Configuracion FastAPI, CORS, middleware, lifespan
├── predictor.py          # Pipeline de inferencia: feature engineering → encode → scale → predict
├── schemas.py            # Esquemas Pydantic (request / response)
├── requirements.txt      # Dependencias del proyecto
├── Dockerfile            # Imagen Docker lista para Render / Railway
├── .env.example          # Variables de entorno de ejemplo
├── models/               # Artefactos de ML serializados (.pkl)
│   ├── xgb_model.pkl
│   ├── scaler.pkl
│   ├── label_encoder_target.pkl
│   ├── feature_encoders.pkl
│   └── feature_names.pkl
└── routers/
    └── cyberattack.py    # Endpoints /cyberattack/predict y /cyberattack/classes
```

### Pipeline de inferencia

```
Input (texto crudo)
    └─► extract_features()    → feat_mitre, feat_tool, feat_target, feat_source
         └─► LabelEncoder     → columnas codificadas numericamente
              └─► StandardScaler → caracteristicas escaladas
                   └─► XGBoost.predict_proba() → distribucion de probabilidades
                        └─► decode (LabelEncoder target) → categoria final + Top-3
```

---

## Instalacion local

### Requisitos previos

- Python 3.11+
- `pip`

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd proyecto-api

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar el servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API quedará disponible en `http://localhost:8000`.

---

## Despliegue con Docker

```bash
# Construir imagen
docker build -t cyberattack-api .

# Ejecutar contenedor
docker run -p 8000:8000 cyberattack-api
```

> El `Dockerfile` esta optimizado para plataformas como **Render** o **Railway** (free tier): imagen slim, un worker Uvicorn, `timeout-keep-alive` de 75 s.

---

## Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/` | Informacion general de la API |
| `GET` | `/health` | Health check (estado del modelo) |
| `POST` | `/cyberattack/predict` | Clasificar un ciberataque |
| `GET` | `/cyberattack/classes` | Listar las 28 categorias soportadas |
| `GET` | `/docs` | Documentacion interactiva (Swagger UI) |
| `GET` | `/redoc` | Documentacion alternativa (ReDoc) |

---

### POST `/cyberattack/predict`

#### Request

```json
{
  "mitre_technique": "T1190 (Exploit Public-Facing Application)",
  "tools_used": "Burp Suite, SQLMap",
  "target_type": "Web Application",
  "source": "OWASP"
}
```

#### Response `200 OK`

```json
{
  "categoria": "Web Application Attack",
  "confianza": 0.8734,
  "top3": [
    { "categoria": "Web Application Attack", "probabilidad": 0.8734 },
    { "categoria": "Injection Attack",        "probabilidad": 0.0812 },
    { "categoria": "Reconnaissance",          "probabilidad": 0.0241 }
  ],
  "features_usadas": {
    "mitre_technique": "T1190 (Exploit Public-Facing Application)",
    "tools_used": "Burp Suite, SQLMap",
    "target_type": "Web Application",
    "source": "OWASP"
  }
}
```

---

### GET `/cyberattack/classes`

#### Response `200 OK`

```json
{
  "n_clases": 28,
  "categorias": [
    "Advanced Persistent Threat (APT)",
    "Cloud Attack",
    "Credential Theft",
    "..."
  ]
}
```

---

### GET `/health`

#### Response `200 OK`

```json
{
  "status": "ok",
  "modelo": "XGBClassifier",
  "n_clases": 28,
  "features": ["feat_mitre", "feat_tool", "feat_target", "feat_source"]
}
```

---

## Categorias soportadas (28 clases)

El modelo clasifica los siguientes tipos de ciberataque basándose en el framework **MITRE ATT&CK**:

> Consulta el endpoint `GET /cyberattack/classes` para obtener la lista completa y actualizada de categorias directamente del modelo en ejecucion.

---

## Variables de entorno

Copia `.env.example` como `.env` y ajusta los valores segun tu entorno:

```bash
cp .env.example .env
```

| Variable | Descripcion | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Cadena de conexion SQLite (desarrollo) | `sqlite:///./app.db` |

---

## Estructura del modelo ML

El modelo fue entrenado con las siguientes etapas de feature engineering:

1. **`feat_mitre`** — Se extrae el primer codigo `T-XXXX` del campo `mitre_technique` con regex.
2. **`feat_tool`** — Se toma la primera herramienta del campo `tools_used`; si no pertenece al Top-50, se agrupa como `"Other"`.
3. **`feat_target`** — Mismo criterio que `feat_tool` sobre el Top-30 de objetivos.
4. **`feat_source`** — Mismo criterio sobre el Top-30 de fuentes.

Cada feature categorica pasa por un `LabelEncoder` individual, luego por un `StandardScaler` global, y finalmente por el clasificador `XGBClassifier`.

---

## Autor

**Alberto Prado**
Proyecto final — Bootcamp Data Science
Junio 2026

---

## Licencia

Uso academico. Todos los derechos reservados © 2026 Alberto Prado.
