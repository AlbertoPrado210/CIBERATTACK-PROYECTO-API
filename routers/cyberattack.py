"""
routers/cyberattack.py
Endpoints de clasificacion multiclase de ciberataques.

Rutas:
  POST  /cyberattack/predict   -> clasifica el tipo de ciberataque
  GET   /cyberattack/classes   -> lista las 28 categorias soportadas
"""

import logging

from fastapi import APIRouter, HTTPException, status

import predictor
from schemas import CyberAttackInput, CyberAttackResponse, Top3Item

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cyberattack",
    tags=["CyberAttack Inference"],
)


@router.post(
    "/predict",
    response_model=CyberAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Clasificar la categoria de un ciberataque",
)
def predict_cyberattack(payload: CyberAttackInput):
    """
    Recibe los indicadores del ataque (tecnica MITRE, herramienta, objetivo y fuente),
    ejecuta el pipeline XGBoost y retorna la categoria predicha con confianza y top-3.

    - **mitre_technique**: Tecnica ATT&CK (ej. T1190, T1078)
    - **tools_used**: Herramientas usadas (ej. Burp Suite, Nmap)
    - **target_type**: Tipo de objetivo (ej. Windows, Web Application)
    - **source**: Fuente de referencia (ej. OWASP, MITRE ATT&CK)
    """
    try:
        result = predictor.predict(
            mitre_technique=payload.mitre_technique,
            tools_used=payload.tools_used,
            target_type=payload.target_type,
            source=payload.source,
        )
    except FileNotFoundError as exc:
        logger.error("Artefacto de ciberataques no disponible: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo de clasificacion no disponible. Contacte al administrador.",
        )
    except Exception as exc:
        logger.exception("Error en clasificacion de ciberataque: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno durante la inferencia: {str(exc)}",
        )

    return CyberAttackResponse(
        categoria=result["categoria"],
        confianza=result["confianza"],
        top3=[Top3Item(**item) for item in result["top3"]],
        features_usadas={
            "mitre_technique": payload.mitre_technique,
            "tools_used":      payload.tools_used,
            "target_type":     payload.target_type,
            "source":          payload.source,
        },
    )


@router.get(
    "/classes",
    status_code=status.HTTP_200_OK,
    summary="Listar las 28 categorias de ciberataques soportadas",
)
def list_classes():
    """
    Retorna la lista completa de categorias que el modelo puede predecir.
    Util para documentacion, validacion en frontends y pruebas de integracion.
    """
    try:
        art = predictor._load_artifacts()
        classes = art["le_target"].classes_.tolist()
    except Exception as exc:
        logger.error("Error al obtener clases del modelo: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no disponible para consultar clases.",
        )

    return {
        "n_clases": len(classes),
        "categorias": classes,
    }
