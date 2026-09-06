# Métricas reproducibles del repositorio

Este documento evita presentar LOC como calidad. Antes de escribir cifras, ejecutar:

```bash
python -m pytest --collect-only -q
find app evaluation tests android/app/src -type f | sort
rg -n '^(@app\.|@router\.|@.*\.(get|post|put|delete))' app
rg -n '^class .*\(Base\)|^class .*\(.*Model' app/models.py
find docs/decisions -name '*.md' | sort
```

El resultado debe fecharse y etiquetarse como MEDIDO. No se registra aquí una cifra
estática porque las ramas #5/#6/#7 tienen conjuntos de tests y módulos distintos.
