import anthropic
import json
import re

client = anthropic.Anthropic()

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
    """Build a compact company context string to minimize tokens."""
    services = ", ".join(company.get("services", []))
    usp = company.get("usp", "")
    tone = company.get("tone", "professionale")
    target = company.get("target", "B2C")
    city = company.get("city", "")
    sector = company.get("sector", "")

    return (
        f"Nome: {company['name']} | Settore: {sector} | Città sede: {city} | "
        f"Servizi: {services} | Target: {target} | Tono: {tone} | "
        f"USP: {usp} | Tel: {company.get('phone','')} | Email: {company.get('email','')} | "
        f"Sito: {company.get('website','')} | Anno fondazione: {company.get('founding_year','')}"
    )


def build_geo_block(geo_context: dict) -> str:
    """Build compact geo context string."""
    if not geo_context:
        return ""
    pois = geo_context.get("poi_text", "")
    climate = geo_context.get("climate", "")
    region = geo_context.get("region", "")
    return f"Regione: {region} | Clima: {climate} | POI locali: {pois}"


def build_existing_block(scraped_data: dict) -> str:
    """Build existing content block from scraped page."""
    if not scraped_data or not scraped_data.get("success"):
        return ""
    title = scraped_data.get("title", "")
    body = scraped_data.get("body_text", "")[:800]
    return f"\nContenuto attuale da ottimizzare — Titolo: {title} | Testo: {body}"


def generate_page_content(
    page_type: str,
    company: dict,
    geo_context: dict = None,
    scraped_data: dict = None,
    service_name: str = None,
    city: str = None,
) -> dict:
    """Generate optimized content for a page using Claude Haiku."""

    company_block = build_company_block(company)
    geo_block = build_geo_block(geo_context) if geo_context else ""
    existing_block = build_existing_block(scraped_data) if scraped_data else ""

    if page_type == "city_page" and geo_context:
        prompt = PAGE_PROMPTS["city_page"].format(
            company_block=company_block,
            city=city or geo_context.get("city", ""),
            region=geo_context.get("region", ""),
            climate=geo_context.get("climate", ""),
            pois=geo_context.get("poi_text", ""),
            services=", ".join(company.get("services", []))
        )
    elif page_type == "servizio" and service_name:
        prompt = PAGE_PROMPTS["servizio"].format(
            company_block=company_block,
            service_name=service_name,
            geo_block=geo_block,
            existing_block=existing_block
        )
    else:
        template = PAGE_PROMPTS.get(page_type, PAGE_PROMPTS["home"])
        prompt = template.format(
            company_block=company_block,
            geo_block=geo_block,
            existing_block=existing_block,
            service_name=service_name or ""
        )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    raw = raw.strip()

    try:
        content = json.loads(raw)
    except json.JSONDecodeError:
        content = {"error": "JSON parse failed", "raw": raw}

    return {
        "content": content,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
