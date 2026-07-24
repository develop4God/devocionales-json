# devocionales-json

[![JSON_CI](https://github.com/develop4God/devocionales-json/actions/workflows/ci.yml/badge.svg)](https://github.com/develop4God/devocionales-json/actions/workflows/ci.yml)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

---

**[English](#english)** | **[Español](#español)**

---

<a name="english"></a>

## 🇺🇸 English

Generated biblical content consumed by the [devocional_nuevo](../devocional_nuevo) app.

**📚 Content & Study**
- **Daily or On-Demand Devotionals**: Updated spiritual content in multiple Bible versions
- **Discovery Studies**: Learning from the Word of God
- **Encounters**: Connect with Jesus Christ as never before

### 📖 Devocionales

<!-- README-STATS:devocionales -->
| Lang | Versions | Files (2025 + 2026) | Entries |
|---|---|---|---|
| ar | NAV, SVDA | 4 | 1,460 |
| de | LU17, SCH2000 | 4 | 1,460 |
| en | KJV, NIV | 4 | 1,460 |
| es | NVI, RVR1960 | 4 | 1,460 |
| fil | ASND, MBB05 | 4 | 1,460 |
| fr | LSG1910, TOB | 4 | 1,460 |
| hi | HERV, HIOV | 4 | 1,460 |
| ja | リビングバイブル, 新改訳2003 | 4 | 1,460 |
| pt | ARC, NVI | 4 | 1,460 |
| zh | 和合本1919, 新译本 | 4 | 1,460 |

**Total: 40 files · 14,600 entries · 10 languages · 20 Bible versions**
<!-- /README-STATS:devocionales -->

### ✨ Discovery & Encounters

<!-- README-STATS:discovery -->
**Discovery** — 38 studies × 10 languages (ar, de, en, es, fil, fr, hi, ja, pt, zh) — 380 files.
<!-- /README-STATS:discovery -->

<!-- README-STATS:encounters -->
**Encounters** — 14 encounters × 10 languages (ar, de, en, es, fil, fr, hi, ja, pt, zh) — 140 files.
<!-- /README-STATS:encounters -->

### 🏗️ Directory structure

<!-- README-STATS:directory-structure -->
```
devocionales-json/
├── archive/
├── badges/
├── bible_database/
├── devocionales_scripts/
├── discovery/
├── encounters/
├── shared_validation/
└── tests/
```
<!-- /README-STATS:directory-structure -->

### 🧪 Validation

CI (`.github/workflows/ci.yml`) runs on every PR and push to `main`, gating **Discovery and Encounters only**:

| Job | What it does |
|---|---|
| Tests + Validators | unittest suite, Discovery master validator, Encounters master validator |
| Scripture Validation | Scripture-reference checks for Discovery and Encounters |

> Devocionales files are **not** currently gated in CI — run the validator below manually before merging changes to `Devocional_year_*.json`.

**Devocionales:**
```bash
# Full phased pipeline (lint, index, Bible-versions SOT, per-file corpus checks)
python3 devocionales_scripts/devocionales_master_validator.py

# Cross-file duplicate ID check
python3 devocionales_scripts/validate_duplicates.py

# Single-file validator (GUI with no args, or --file for CLI)
python3 devocionales_scripts/validate_devocional_gui.py --file <path>.json
```

📖 **[devocionales_scripts/README.md](./devocionales_scripts/README.md)** — full validator reference

**Discovery / Encounters:**
```bash
python3 discovery/discovery_scripts/discovery_master_validator.py
python3 encounters/encounters_scripts/encounters_master_validator.py
```

📖 **[discovery_scripts/README.md](./discovery/discovery_scripts/README.md)** · **[encounters_scripts/](./encounters/encounters_scripts/)**

📖 **[shared_validation/README.md](./shared_validation/README.md)** — validation helpers shared across all three corpora

### 🤝 Contributing

If you'd like to suggest a new language, report an issue with the data, or propose an improvement, please open an issue or pull request. Or just contact us!

### 📄 License

This work is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to:

- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material

Under the following terms:

- **Attribution (BY)** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
- **NonCommercial (NC)** — You may not use the material for commercial purposes.

For the full license text, see the [LICENSE](./LICENSE) file or visit:

- Summary: https://creativecommons.org/licenses/by-nc/4.0/
- Legal Code: https://creativecommons.org/licenses/by-nc/4.0/legalcode

---

<a name="español"></a>

## 🇪🇸 Español

Contenido bíblico generado que consume la app [devocional_nuevo](../devocional_nuevo).

**📚 Contenido y Estudio**
- **Devocionales Diarios o Bajo Demanda**: Contenido espiritual actualizado en múltiples versiones de la Biblia
- **Estudios Discovery**: Aprendiendo de la Palabra de Dios
- **Encuentros**: Conecta con Jesucristo como nunca antes

### 📖 Devocionales

Ver la tabla en la sección en inglés arriba (los datos son iguales para ambos idiomas).

### ✨ Discovery & Encuentros

Ver la sección en inglés arriba (los datos son iguales para ambos idiomas).

### 🏗️ Estructura de directorios

Ver la sección en inglés arriba (la estructura es igual para ambos idiomas).

### 🧪 Validación

CI (`.github/workflows/ci.yml`) se ejecuta en cada PR y push a `main`, validando **únicamente Discovery y Encounters**:

| Job | Qué hace |
|---|---|
| Tests + Validators | suite de unittest, validador maestro de Discovery, validador maestro de Encounters |
| Scripture Validation | verificación de referencias bíblicas para Discovery y Encounters |

> Los archivos de Devocionales **no** están actualmente validados en CI — ejecuta el validador manualmente antes de hacer merge de cambios a `Devocional_year_*.json`.

**Devocionales:**
```bash
# Pipeline completo por fases (lint, índice, SOT de versiones bíblicas, validación por archivo)
python3 devocionales_scripts/devocionales_master_validator.py

# Verificación de IDs duplicados entre archivos
python3 devocionales_scripts/validate_duplicates.py

# Validador de un solo archivo (GUI sin argumentos, o --file para CLI)
python3 devocionales_scripts/validate_devocional_gui.py --file <ruta>.json
```

📖 **[devocionales_scripts/README.md](./devocionales_scripts/README.md)** — referencia completa de validadores

**Discovery / Encounters:**
```bash
python3 discovery/discovery_scripts/discovery_master_validator.py
python3 encounters/encounters_scripts/encounters_master_validator.py
```

📖 **[discovery_scripts/README.md](./discovery/discovery_scripts/README.md)** · **[encounters_scripts/](./encounters/encounters_scripts/)**

📖 **[shared_validation/README.md](./shared_validation/README.md)** — helpers de validación compartidos entre los tres corpus

### 🤝 Contribuir

Si deseas sugerir un nuevo idioma, reportar un problema con los datos o proponer una mejora, abre un issue o pull request. ¡O simplemente contáctanos!

### 📄 Licencia

Este trabajo está licenciado bajo la [Licencia Creative Commons Atribución-NoComercial 4.0 Internacional (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/deed.es).

Puedes:

- **Compartir** — copiar y redistribuir el material en cualquier medio o formato
- **Adaptar** — remezclar, transformar y construir sobre el material

Bajo las siguientes condiciones:

- **Atribución (BY)** — Debes dar crédito adecuado, proporcionar un enlace a la licencia e indicar si se realizaron cambios.
- **NoComercial (NC)** — No puedes utilizar el material con fines comerciales.

Para el texto completo de la licencia, ver el archivo [LICENSE](./LICENSE) o visitar:

- Resumen: https://creativecommons.org/licenses/by-nc/4.0/deed.es
- Código Legal: https://creativecommons.org/licenses/by-nc/4.0/legalcode.es

---

## 📬 Contact / Contacto

Questions or support / Preguntas o soporte: develop4god@gmail.com
Website / Sitio web: https://www.develop4God.com

---

© 2026 develop4God
