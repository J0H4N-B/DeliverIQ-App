# 📦 DeliverIQ — Clasificador de Calidad de Entregas

Aplicación web de Machine Learning que entrena un modelo de clasificación
sobre cualquier CSV de entregas y predice si una entrega será **Exitosa**,
**Demorada** o **Fallida**.

## 🛠️ Stack

| Capa        | Tecnología                                        |
|-------------|---------------------------------------------------|
| Backend     | Python 3.9+ · Flask · Blueprints                 |
| ML          | scikit-learn · joblib                            |
| Visualización | matplotlib · seaborn                           |
| Datos       | Pandas · CSV                                     |
| Frontend    | HTML · CSS · JavaScript · Boxicons              |

## 🚀 Instalación

```bash
git clone https://github.com/J0H4N-B/clasificador-entregas.git
cd clasificador-entregas

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env          # Edita SECRET_KEY

python run.py
# http://localhost:5000
```

## 📁 Estructura

```
proyecto4_clasificador/
├── run.py
├── config.py
├── requirements.txt
├── .env.example
├── data/
│   ├── samples/
│   │   └── entregas_ejemplo.csv
│   ├── uploads/
├── app/
│   ├── __init__.py
│   ├── blueprints/
│   │   ├── main.py
│   │   ├── upload.py         ← /api/upload/*
│   │   └── model.py          ← /api/model/*
│   └── utils/
│       ├── file_handler.py   ← CSV seguro
│       └── ml_engine.py      ← Pipeline ML completo
└── templates/
    └── index.html
```

## ✨ Flujo de uso

```
1. Subir CSV  →  2. Configurar target + algoritmo  →
3. Entrenar  →  4. Ver resultados  →  5. Predecir
```

## 🤖 Modelos disponibles

| Modelo              | Descripción                                           | Feature Importance |
|---------------------|-------------------------------------------------------|--------------------|
| Random Forest       | Robusto, maneja datos mixtos bien                     | ✅                 |
| Gradient Boosting   | Alta precisión, más lento de entrenar                  | ✅                 |
| Regresión Logística | Rápido e interpretable, ideal para relaciones lineales | ✅ (coeficientes)  |
| Extra Trees         | Más rápido que Random Forest, menos overfitting        | ✅                 |
| SVM (RBF)           | Fronteras complejas, kernel radial                     | ❌                 |
| K-Nearest Neighbors | Clasifica por vecinos cercanos                         | ❌                 |
| Árbol de Decisión   | Muy interpretable, reglas de decisión visibles         | ✅                 |
| Naive Bayes         | Extremadamente rápido, asume independencia             | ❌                 |

> **Nota:** Los modelos sin feature importance (SVM, KNN, Naive Bayes) muestran
> un mensaje informativo en lugar del gráfico.

## ➕ Agregar un nuevo modelo

Edita `app/utils/ml_engine.py` y añade una entrada en `AVAILABLE_MODELS`:

```python
"xgboost": {
    "label": "XGBoost",
    "description": "Extreme Gradient Boosting. Muy rápido y preciso.",
    "class": XGBClassifier,  # importa primero
    "params": {"n_estimators": 100, "max_depth": 5, "random_state": 42},
}
```

Reinicia la app y aparecerá automáticamente en el selector de algoritmos.

## 📊 Resultados incluidos

- **Accuracy** en conjunto de prueba
- **Cross-validation** con 5 folds
- **Matriz de confusión** (gráfico)
- **Feature importance** (gráfico + barras) — cuando aplica
- **Distribución de clases** (gráfico)
- **Reporte por clase**: precisión, recall, F1-score

## 🔒 Seguridad

- Solo `.csv` permitido · UUID único por archivo
- Ruta del archivo en sesión del servidor
- Columnas validadas contra el DataFrame real
- Límite de 50 000 filas
- Carpeta `data/models` creada automáticamente si no existe

## 📄 Licencia

MIT
