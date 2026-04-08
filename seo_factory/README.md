# SEO/GEO Factory — Tool interno

Genera contenuti ottimizzati SEO + geo-targeting e i rispettivi JSON-LD Schema.org.

## Setup

```bash
# 1. Crea un ambiente virtuale (consigliato)
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# 2. Installa le dipendenze
pip install -r requirements.txt

# 3. Avvia il tool
streamlit run app.py
```

## Cosa ti serve

- **Python 3.9+**
- **API Key Anthropic** (inserita nella sidebar del tool)
- Connessione internet (per OpenStreetMap e scraping)

## Come usare il tool

### Tab 1 — Dati Azienda
Compila tutti i campi disponibili. Più dati inserisci, migliore sarà il contenuto generato.
Campi obbligatori: Nome azienda, Settore, Servizi, USP.

### Tab 2 — Pagine & Modalità
Scegli tra:
- **Sito nuovo**: genera tutto da zero
- **Sito esistente**: inserisci gli URL e il tool legge il contenuto attuale per ottimizzarlo

Seleziona le pagine da generare (max 5 servizi per contenere i costi).

### Tab 3 — Geo Targeting
Inserisci le città target. Il tool suggerisce automaticamente città vicine nella stessa regione.
Abilita "City Pages" nel Tab 2 per generare una pagina ottimizzata per ogni città.

### Tab 4 — Genera & Esporta
Avvia la generazione. Al termine scarica il file ZIP con tutti i JSON.

## Output

Per ogni pagina viene generato un file JSON contenente:
- `seo`: meta_title, meta_description, H1
- `content`: tutti i blocchi di testo (intro, corpo, trust block, ecc.)
- `faq_html`: codice HTML delle FAQ con markup Schema.org inline
- `schema_jsonld`: array di tutti gli schema JSON-LD per la pagina
- `schema_html_tags`: i tag `<script type="application/ld+json">` pronti da copiare nell'HTML

## Costi stimati

| Configurazione | Pagine | Costo stimato |
|---|---|---|
| Solo pagine core (Home + Chi siamo + FAQ) | 3 | ~$0.004 |
| + 3 servizi | 6 | ~$0.008 |
| + 5 city pages | 11 | ~$0.015 |
| Completo (10 city pages + 5 servizi) | 18 | ~$0.025 |

I costi sono contenuti grazie a:
1. **Claude Haiku** (modello più economico)
2. **JSON-LD generati da codice Python** (zero token per gli schema)
3. **Un solo prompt per pagina** (meta + corpo + FAQ in una chiamata)
4. **Prompt compressi** con variabili invece di testo libero

## Struttura file

```
seo_factory/
├── app.py                    # Applicazione Streamlit (interfaccia)
├── requirements.txt
├── core/
│   ├── scraper.py           # Lettura pagine esistenti
│   ├── geo_enricher.py      # Dati geografici (OSM + clima)
│   ├── ai_generator.py      # Generazione contenuti via Claude Haiku
│   └── output_builder.py    # Assemblaggio JSON finale
├── schemas/
│   └── generators.py        # JSON-LD generati da Python
└── output/                  # Cartella output (creata automaticamente)
    └── cliente_timestamp/
        ├── home.json
        ├── chi_siamo.json
        ├── servizio_nome.json
        ├── faq.json
        ├── city_milano.json
        └── _report.json
```
