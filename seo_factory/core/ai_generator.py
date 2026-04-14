import anthropic
import json
import re

# Rimosso il client globale per evitare errori di inizializzazione senza chiave

PAGE_PROMPTS = {
    "home": """Sei un copywriter SEO esperto. Scrivi i contenuti ottimizzati per la HOME PAGE.
Rispondi SOLO con JSON valido, nessun testo extra, nessun markdown.

Dati azienda: {company_block}
Contesto geo: {geo_block}
{existing_block}

Genera un JSON con questa struttura esatta:
{{
  "meta_title": "titolo SEO max 60 caratteri con keyword principale e città",
  "meta_description": "descrizione SEO max 155 caratteri con call to action",
  "h1": "headline principale della pagina",
  "intro": "paragrafo introduttivo 80-100 parole, con keyword geografica naturale",
  "services_overview": "paragrafo 60-80 parole che elenca i servizi principali",
  "trust_block": "paragrafo 50-70 parole su esperienza, valori, EEAT (esperienza reale, autorevolezza)",
  "cta_text": "testo call to action 15-20 parole",
  "faqs": [
    {{"question": "domanda frequente 1 specifica per settore e geo", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda frequente 2", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda frequente 3", "answer": "risposta 40-60 parole"}}
  ]
}}""",

    "chi_siamo": """Sei un copywriter SEO esperto. Scrivi i contenuti per la pagina CHI SIAMO.
Rispondi SOLO con JSON valido, nessun testo extra, nessun markdown.

Dati azienda: {company_block}
{existing_block}

Genera un JSON con questa struttura esatta:
{{
  "meta_title": "titolo SEO max 60 caratteri",
  "meta_description": "descrizione SEO max 155 caratteri",
  "h1": "headline principale",
  "storia": "paragrafo storia aziendale 80-100 parole, con anno fondazione se disponibile, EEAT forte",
  "missione": "paragrafo missione e valori 60-80 parole",
  "team_intro": "paragrafo sul team 50-70 parole, competenze e professionalità",
  "perche_noi": "paragrafo differenziazione 60-80 parole con USP reali",
  "faqs": [
    {{"question": "domanda su chi siete / esperienza", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda su qualifiche / certificazioni", "answer": "risposta 40-60 parole"}}
  ]
}}""",

    "servizio": """Sei un copywriter SEO esperto. Scrivi i contenuti per la pagina SERVIZIO.
Rispondi SOLO con JSON valido, nessun testo extra, nessun markdown.

Dati azienda: {company_block}
Servizio specifico: {service_name}
Contesto geo: {geo_block}
{existing_block}

Genera un JSON con questa struttura esatta:
{{
  "meta_title": "titolo SEO max 60 caratteri con servizio e città",
  "meta_description": "descrizione SEO max 155 caratteri con call to action",
  "h1": "headline principale con servizio e zona geografica",
  "intro": "paragrafo introduttivo 80-100 parole sul servizio, con riferimento geografico",
  "cosa_offriamo": "paragrafo 80-100 parole su cosa include il servizio",
  "perche_sceglierci": "paragrafo 60-80 parole su vantaggi e differenziatori",
  "processo": "paragrafo 50-70 parole su come lavoriamo, step del processo",
  "faqs": [
    {{"question": "domanda specifica sul servizio {service_name}", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda su prezzi o tempi", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda su zona di intervento", "answer": "risposta 40-60 parole"}}
  ]
}}""",

    "faq": """Sei un copywriter SEO esperto. Scrivi i contenuti per la pagina FAQ.
Rispondi SOLO con JSON valido, nessun testo extra, nessun markdown.

Dati azienda: {company_block}
Contesto geo: {geo_block}

Genera un JSON con questa struttura esatta:
{{
  "meta_title": "titolo SEO max 60 caratteri",
  "meta_description": "descrizione SEO max 155 caratteri",
  "h1": "headline principale",
  "intro": "breve introduzione 40-50 parole",
  "faqs": [
    {{"question": "domanda 1 specifica per settore", "answer": "risposta completa 60-80 parole"}},
    {{"question": "domanda 2 su prezzi/costi", "answer": "risposta 60-80 parole"}},
    {{"question": "domanda 3 su zone coperte", "answer": "risposta 60-80 parole"}},
    {{"question": "domanda 4 su tempi/disponibilità", "answer": "risposta 60-80 parole"}},
    {{"question": "domanda 5 su garanzie", "answer": "risposta 60-80 parole"}},
    {{"question": "domanda 6 settore specifico", "answer": "risposta 60-80 parole"}},
    {{"question": "domanda 7 su come contattarvi", "answer": "risposta 60-80 parole"}}
  ]
}}""",

    "city_page": """Sei un copywriter SEO esperto. Scrivi i contenuti per una CITY PAGE (pagina geo-targeting).
Rispondi SOLO con JSON valido, nessun testo extra, nessun markdown.

Dati azienda: {company_block}
Città target: {city}
Regione: {region}
Clima locale: {climate}
Punti di interesse reali: {pois}
Servizi offerti: {services}

Genera una pagina UNICA per questa città (NON generica, usa i dati locali reali).
JSON con questa struttura esatta:
{{
  "meta_title": "titolo SEO max 60 caratteri con servizio + città",
  "meta_description": "descrizione SEO max 155 caratteri specifica per {city}",
  "h1": "headline con servizio e {city}",
  "intro_locale": "paragrafo 80-100 parole specifico per {city}, cita il contesto locale reale",
  "servizi_in_citta": "paragrafo 80-100 parole su come operiamo a {city} e dintorni",
  "contesto_territoriale": "paragrafo 60-80 parole che usa dati locali (clima, territorio, POI) per contestualizzare il servizio",
  "perche_noi_locale": "paragrafo 50-60 parole con riferimento alla zona di {city}",
  "faqs": [
    {{"question": "Operate a {city} e provincia?", "answer": "risposta specifica 40-60 parole"}},
    {{"question": "Quali zone di {city} coprite?", "answer": "risposta 40-60 parole"}},
    {{"question": "domanda specifica sul servizio a {city}", "answer": "risposta 40-60 parole"}}
  ]
}}"""
}


def build_company_block(company: dict) -> str:
    services = ", ".join
