# Corrections par rapport à l'énoncé :
# * Python 3.12 partout (poste Ubuntu 24.04, image, CI) : un modèle sérialisé avec
#   joblib n'est fiable qu'avec les mêmes versions de Python et scikit-learn ;
# * le dataset et le modèle sont produits pendant le build, avec les versions
#   installées dans l'image : plus d'image construite sans models/model.pkl ;
# * .dockerignore pour ne pas copier .venv, .git, logs ;
# * utilisateur non root, HEALTHCHECK, variables d'environnement Python.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Couche de dépendances (mise en cache tant que requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY api/ api/
COPY frontend/ frontend/

# Entraînement reproductible dans l'image
ARG MODEL_VERSION=1.0.0
ENV MODEL_VERSION=${MODEL_VERSION}
RUN python src/generate_data.py && python src/train.py

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app
USER appuser

ENV LOG_FILE=/app/logs/api.log

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
