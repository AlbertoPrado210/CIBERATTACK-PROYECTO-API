"""
schemas.py
Esquemas Pydantic v2 para la validacion de datos de la API de ciberataques.
"""

from pydantic import BaseModel, Field


class CyberAttackInput(BaseModel):
    mitre_technique: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tecnica(s) MITRE ATT&CK. Ej: 'T1190 (Exploit Public-Facing App)'",
        examples=["T1190 (Exploit Public-Facing Application)"],
    )
    tools_used: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Herramienta(s) utilizadas, separadas por coma. Ej: 'Burp Suite, SQLMap'",
        examples=["Burp Suite, SQLMap"],
    )
    target_type: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Tipo(s) de objetivo del ataque. Ej: 'Web Application'",
        examples=["Web Application"],
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Fuente(s) de referencia. Ej: 'OWASP, MITRE ATT&CK'",
        examples=["OWASP"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "mitre_technique": "T1190 (Exploit Public-Facing Application)",
                "tools_used":      "Burp Suite, SQLMap",
                "target_type":     "Web Application",
                "source":          "OWASP",
            }
        }
    }


class Top3Item(BaseModel):
    categoria:    str
    probabilidad: float


class CyberAttackResponse(BaseModel):
    categoria:       str            = Field(..., description="Categoria de ataque predicha")
    confianza:       float          = Field(..., description="Probabilidad de la clase ganadora (0-1)")
    top3:            list[Top3Item] = Field(..., description="Top 3 categorias mas probables")
    features_usadas: dict           = Field(..., description="Campos enviados en el request")
