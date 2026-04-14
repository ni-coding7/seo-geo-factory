import streamlit as st
import json
import os
import sys
import zipfile
import io
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Config prezzi (unico posto da aggiornare) ---
PRICING = {
    "input_per_token": 0.00000025,
    "output_per_token": 0.00000125,
}
AVG_INPUT_TOKENS = 450
AVG_OUTPUT_TOKENS = 900

# --- Carica API key da st.secrets se disponibile (NON scrivere in os.environ globale) ---
_secrets_key = None
try:
    _secrets_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

from core.scraper import scrape_multiple
from core.geo_enricher import get_city_context, get_suggested_cities
from core.ai_generator import generate_page_content
from core.output_builder import assemble_page_output, save_client_output

st.set_page_config(
    page_title="SEO/GEO Factory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp { max-width: 1200px; margin: 0 auto; }
.step-header { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
.cost-badge {
    background: #e8f5e9; color: #2e7d32;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.85rem; font-weight: 500;
    display: inline-block; margin: 4px 0;
}
.warning-badge {
    background: #fff3e0; color: #e65100;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# --- Inizializzazione session_state completa ---
defaults = {
    "generated_pages": [],
    "token_report": {"total_input": 0, "total_output": 0, "pages": []},
    "output_dir": None,
    "api_key": _secrets_key or "",
    "is_running": False,
    # variabili condivise tra tab
    "gen_home": True,
    "gen_chi_siamo": True,
    "gen_faq": True,
    "gen_servizi": True,
    "gen_city": False,
    "selected_services": [],
    "all_cities": [],
    "mode": "🆕 Sito nuovo — crea da zero",
    "existing_urls": {},
    "n_pages": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def get_api_key() -> str:
    """Restituisce la API key senza mai esporla in os.environ globale."""
    return st.session_state.get("api_key") or _secrets_key or ""


def is_valid_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def estimate_cost(n_pages: int) -> float:
    cost = (
        AVG_INPUT_TOKENS * n_pages * PRICING["input_per_token"]
        + AVG_OUTPUT_TOKENS * n_pages * PRICING["output_per_token"]
    )
    return round(cost, 4)


def compute_actual_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens * PRICING["input_per_token"]
        + output_tokens * PRICING["output_per_token"],
        4,
    )


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ SEO/GEO Factory")
    st.caption("Tool interno — generazione contenuti ottimizzati")
    st.divider()
    st.markdown("**Flusso di lavoro:**")
    st.markdown("1. Dati azienda\n2. Modalità e pagine\n3. Geo targeting\n4. Genera\n5. Esporta")
    st.divider()

    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state["api_key"],
        help="La chiave viene usata solo per questa sessione e non viene salvata",
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input
        st.success("API Key impostata")
    elif st.session_state.get("api_key"):
        st.success("API Key attiva")

st.title("SEO/GEO Content Factory")
st.caption("Genera contenuti ottimizzati per SEO e geo-targeting. Compila i dati aziendali e avvia la generazione.")

tab1, tab2, tab3, tab4 = st.tabs(["① Dati Azienda", "② Pagine & Modalità", "③ Geo Targeting", "④ Genera & Esporta"])

# ── Tab 1: Dati Azienda ───────────────────────────────────────────────────────
with tab1:
    st.subheader("Dati aziendali")
    st.caption("Questi dati vengono usati per costruire contenuti coerenti e gli schema JSON-LD.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Informazioni principali**")
        company_name = st.text_input("Nome azienda / Brand *", placeholder="es. Idrotech Srl")
        sector = st.text_input("Settore *", placeholder="es. Idraulica industriale")
        website = st.text_input("Sito web", placeholder="https://www.esempio.it")
        phone = st.text_input("Telefono", placeholder="+39 02 1234567")
        email = st.text_input("Email", placeholder="info@esempio.it")
        founding_year = st.text_input("Anno fondazione", placeholder="es. 2005")

    with col2:
        st.markdown("**Sede e posizione**")
        has_physical = st.radio("Tipo attività", ["Ha sede fisica", "Servizio a domicilio / remoto"], index=0)
        address = st.text_input("Indirizzo", placeholder="Via Roma 10")
        company_city = st.text_input("Città sede", placeholder="Milano")
        postal_code = st.text_input("CAP", placeholder="20121")
        price_range = st.selectbox("Fascia di prezzo", ["€", "€€", "€€€", "€€€€"])
        logo_url = st.text_input("URL logo (opzionale)", placeholder="https://...")

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Servizi offerti** (max 8)")
        services_raw = st.text_area(
            "Un servizio per riga *",
            placeholder="Elettropompe sommerse\nPompe centrifughe\nManutenzione impianti",
            height=120,
        )
        st.markdown("**Proposta di valore (USP)**")
        usp = st.text_area(
            "Cosa vi distingue dalla concorrenza? *",
            placeholder="20 anni di esperienza, assistenza 24/7...",
            height=80,
        )

    with col4:
        st.markdown("**Comunicazione**")
        target = st.selectbox("Target cliente", ["B2B", "B2C", "B2B + B2C"])
        tone = st.selectbox(
            "Tono di voce",
            ["Professionale e tecnico", "Friendly e accessibile", "Autorevole e formale", "Diretto e concreto"],
        )
        st.markdown("**Profili social (opzionale)**")
        social_raw = st.text_area(
            "Un profilo per riga",
            placeholder="https://www.facebook.com/esempio\nhttps://www.linkedin.com/company/esempio",
            height=70,
        )
        st.markdown("**Orari apertura (opzionale)**")
        opening_hours_raw = st.text_input("Formato Schema.org", placeholder="Mo-Fr 09:00-18:00, Sa 09:00-13:00")

    st.divider()
    st.markdown("**Descrizione breve azienda**")
    description = st.text_area(
        "Descrizione in 2-3 frasi",
        placeholder="Idrotech Srl è specializzata nella fornitura e manutenzione di pompe industriali in Lombardia...",
        height=80,
    )

    company_data = {
        "name": company_name,
        "sector": sector,
        "website": website,
        "phone": phone,
        "email": email,
        "founding_year": founding_year,
        "address": address,
        "city": company_city,
        "postal_code": postal_code,
        "price_range": price_range,
        "has_physical_location": has_physical == "Ha sede fisica",
        "logo_url": logo_url,
        "services": [s.strip() for s in services_raw.split("\n") if s.strip()],
        "usp": usp,
        "target": target,
        "tone": tone,
        "social_profiles": [s.strip() for s in social_raw.split("\n") if s.strip()],
        "opening_hours": opening_hours_raw,
        "description": description,
    }

# ── Tab 2: Pagine & Modalità ──────────────────────────────────────────────────
with tab2:
    st.subheader("Modalità e pagine da generare")

    mode = st.radio(
        "**Modalità operativa**",
        ["🆕 Sito nuovo — crea da zero", "🔄 Sito esistente — ottimizza"],
        help="Per siti esistenti puoi inserire gli URL e il tool legge il contenuto attuale",
    )
    st.session_state["mode"] = mode

    st.divider()
    st.markdown("**Pagine core da generare**")
    col1, col2 = st.columns(2)
    with col1:
        gen_home = st.checkbox("Home page", value=True)
        gen_chi_siamo = st.checkbox("Chi siamo", value=True)
        gen_faq = st.checkbox("Pagina FAQ", value=True)
    with col2:
        gen_servizi = st.checkbox("Pagine Servizio", value=True)
        gen_city = st.checkbox("City Pages (geo-targeting)", value=False)

    # Persisti in session_state
    st.session_state["gen_home"] = gen_home
    st.session_state["gen_chi_siamo"] = gen_chi_siamo
    st.session_state["gen_faq"] = gen_faq
    st.session_state["gen_servizi"] = gen_servizi
    st.session_state["gen_city"] = gen_city

    if gen_servizi and company_data["services"]:
        st.markdown("**Seleziona i servizi per cui generare una pagina** (max 5)")
        selected_services = st.multiselect(
            "Servizi",
            options=company_data["services"],
            default=company_data["services"][:3],
            max_selections=5,
        )
    else:
        selected_services = []
    st.session_state["selected_services"] = selected_services

    n_pages = (
        (1 if gen_home else 0)
        + (1 if gen_chi_siamo else 0)
        + (1 if gen_faq else 0)
        + len(selected_services)
    )
    st.session_state["n_pages"] = n_pages

    estimated_cost = estimate_cost(n_pages)
    st.markdown(
        f'<span class="cost-badge">💰 Stima costo: ~${estimated_cost} USD ({n_pages} pagine core)</span>',
        unsafe_allow_html=True,
    )

    if mode == "🔄 Sito esistente — ottimizza":
        st.divider()
        st.markdown("**URL pagine esistenti** (opzionale)")
        st.caption("Inserisci gli URL delle pagine da ottimizzare. URL non validi vengono ignorati.")
        col1, col2 = st.columns(2)
        with col1:
            url_home = st.text_input("URL Home", placeholder="https://www.esempio.it/")
            url_chi_siamo = st.text_input("URL Chi siamo", placeholder="https://www.esempio.it/chi-siamo/")
            url_faq = st.text_input("URL FAQ", placeholder="https://www.esempio.it/faq/")
        with col2:
            url_servizi_raw = st.text_area(
                "URL Servizi (uno per riga)",
                placeholder="https://www.esempio.it/elettropompe/\nhttps://www.esempio.it/manutenzione/",
                height=100,
            )

        # Valida gli URL prima di usarli
        invalid_urls = [u for u in [url_home, url_chi_siamo, url_faq] if u and not is_valid_url(u)]
        if invalid_urls:
            st.warning(f"⚠️ URL non validi (verranno ignorati): {', '.join(invalid_urls)}")

        existing_urls = {
            "home": url_home if is_valid_url(url_home) else "",
            "chi_siamo": url_chi_siamo if is_valid_url(url_chi_siamo) else "",
            "faq": url_faq if is_valid_url(url_faq) else "",
            "servizi": [u.strip() for u in url_servizi_raw.split("\n") if u.strip() and is_valid_url(u.strip())],
        }
    else:
        existing_urls = {}
    st.session_state["existing_urls"] = existing_urls

# ── Tab 3: Geo Targeting ──────────────────────────────────────────────────────
with tab3:
    st.subheader("Geo Targeting")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**Città target**")
        cities_raw = st.text_area(
            "Una città per riga",
            placeholder="Milano\nBergamo\nBrescia\nMonza",
            height=150,
        )
        user_cities = [c.strip() for c in cities_raw.split("\n") if c.strip()]

    with col2:
        st.markdown("**Città suggerite**")
        if user_cities:
            suggestions = get_suggested_cities(user_cities)
            if suggestions:
                st.caption("Basate sulla regione delle tue città:")
                extra_cities = st.multiselect("Aggiungi dalle suggerite", suggestions, default=[])
            else:
                st.caption("Nessun suggerimento disponibile per le città inserite")
                extra_cities = []
        else:
            st.caption("Inserisci le città target per vedere i suggerimenti")
            extra_cities = []

    all_cities = list(dict.fromkeys(user_cities + extra_cities))
    st.session_state["all_cities"] = all_cities

    if all_cities:
        st.success(f"**{len(all_cities)} città** selezionate: {', '.join(all_cities)}")
        n_pages_t3 = st.session_state["n_pages"]
        gen_city_t3 = st.session_state["gen_city"]
        total_pages = n_pages_t3 + len(all_cities) if gen_city_t3 else n_pages_t3
        total_cost = estimate_cost(total_pages)
        st.markdown(
            f'<span class="cost-badge">💰 Costo totale stimato (tutte le pagine): ~${total_cost} USD</span>',
            unsafe_allow_html=True,
        )
        if not gen_city_t3:
            st.markdown(
                '<span class="warning-badge">⚠️ Abilita "City Pages" nel Tab 2 per generarle</span>',
                unsafe_allow_html=True,
            )

# ── Tab 4: Genera & Esporta ───────────────────────────────────────────────────
with tab4:
    st.subheader("Genera contenuti")

    # Leggi tutte le variabili da session_state (sicuro anche se tab2/tab3 non visitati)
    _gen_home = st.session_state["gen_home"]
    _gen_chi_siamo = st.session_state["gen_chi_siamo"]
    _gen_faq = st.session_state["gen_faq"]
    _gen_city = st.session_state["gen_city"]
    _selected_services = st.session_state["selected_services"]
    _all_cities = st.session_state["all_cities"]
    _n_pages = st.session_state["n_pages"]
    _mode = st.session_state["mode"]
    _existing_urls = st.session_state["existing_urls"]

    if not company_data["name"] or not company_data["sector"] or not company_data["services"]:
        st.warning("⚠️ Completa almeno: Nome azienda, Settore e Servizi nel Tab 1 prima di generare.")
        st.stop()

    if not get_api_key():
        st.warning("⚠️ Inserisci la tua API Key Anthropic nella sidebar.")
        st.stop()

    total_pages_preview = (
        (1 if _gen_home else 0)
        + (1 if _gen_chi_siamo else 0)
        + (1 if _gen_faq else 0)
        + len(_selected_services)
        + (len(_all_cities) if _gen_city else 0)
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pagine totali", total_pages_preview)
    with col2:
        st.metric("Costo stimato", f"~${estimate_cost(total_pages_preview)} USD")
    with col3:
        st.metric("Città geo-target", len(_all_cities) if _gen_city else 0)

    st.divider()

    # Disabilita il pulsante durante la generazione per evitare doppi click
    if st.button(
        "🚀 Avvia generazione",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["is_running"],
    ):
        st.session_state["is_running"] = True

        # Usa la API key dalla funzione dedicata, non da os.environ
        api_key_for_run = get_api_key()

        st.session_state.generated_pages = []
        st.session_state.token_report = {"total_input": 0, "total_output": 0, "pages": []}

        progress = st.progress(0)
        status = st.empty()
        log = st.empty()

        pages_to_generate = []
        if _gen_home:
            pages_to_generate.append(("home", None, None))
        if _gen_chi_siamo:
            pages_to_generate.append(("chi_siamo", None, None))
        if _gen_faq:
            pages_to_generate.append(("faq", None, None))
        for svc in _selected_services:
            pages_to_generate.append(("servizio", svc, None))
        if _gen_city:
            for city in _all_cities:
                pages_to_generate.append(("city_page", None, city))

        scraped_data = {}
        if _mode == "🔄 Sito esistente — ottimizza" and _existing_urls:
            urls_to_scrape = []
            if _existing_urls.get("home"):
                urls_to_scrape.append(_existing_urls["home"])
            if _existing_urls.get("chi_siamo"):
                urls_to_scrape.append(_existing_urls["chi_siamo"])
            if _existing_urls.get("faq"):
                urls_to_scrape.append(_existing_urls["faq"])
            urls_to_scrape += _existing_urls.get("servizi", [])

            if urls_to_scrape:
                status.info("🔍 Lettura pagine esistenti in corso...")
                scraped_data = scrape_multiple(urls_to_scrape)

        total = len(pages_to_generate)
        generated = []
        input_total = 0
        output_total = 0

        # Cache geo context per città già calcolate (evita chiamate duplicate)
        geo_cache: dict = {}

        for i, (ptype, service, city) in enumerate(pages_to_generate):
            label = (
                city
                if ptype == "city_page"
                else (service if ptype == "servizio" else ptype.replace("_", " ").title())
            )
            status.info(f"⚙️ Generando: **{label}** ({i+1}/{total})")

            geo_ctx = None
            if city:
                if city not in geo_cache:
                    geo_cache[city] = get_city_context(city)
                geo_ctx = geo_cache[city]
            elif company_city:
                if company_city not in geo_cache:
                    geo_cache[company_city] = get_city_context(company_city)
                geo_ctx = geo_cache[company_city] if not scraped_data else None

            existing = None
            if ptype == "home" and _existing_urls.get("home"):
                existing = scraped_data.get(_existing_urls["home"])
            elif ptype == "chi_siamo" and _existing_urls.get("chi_siamo"):
                existing = scraped_data.get(_existing_urls["chi_siamo"])
            elif ptype == "faq" and _existing_urls.get("faq"):
                existing = scraped_data.get(_existing_urls["faq"])

            # Retry con backoff semplice (max 3 tentativi)
            last_exc = None
            for attempt in range(3):
                try:
                    result = generate_page_content(
                        page_type=ptype,
                        company=company_data,
                        geo_context=geo_ctx,
                        scraped_data=existing,
                        service_name=service,
                        city=city,
                        api_key=api_key_for_run,  # passa la chiave esplicitamente
                    )

                    page_output = assemble_page_output(
                        page_type=ptype,
                        content=result["content"],
                        company=company_data,
                        city=city,
                        service_name=service,
                    )

                    generated.append(page_output)
                    input_total += result["input_tokens"]
                    output_total += result["output_tokens"]
                    log.success(f"✓ {label} — {result['input_tokens']}+{result['output_tokens']} token")
                    last_exc = None
                    break

                except Exception as e:
                    last_exc = e
                    if attempt < 2:
                        wait = 2 ** attempt * 2  # 2s, 4s
                        time.sleep(wait)

            if last_exc:
                log.error(f"✗ {label} — Errore dopo 3 tentativi: {str(last_exc)}")

            progress.progress((i + 1) / total)
            time.sleep(0.2)

        st.session_state.generated_pages = generated
        st.session_state.token_report = {
            "total_input": input_total,
            "total_output": output_total,
            "pages": [p["page_type"] for p in generated],
        }

        if generated:
            output_dir = save_client_output(
                company_data["name"],
                generated,
                st.session_state.token_report,
            )
            st.session_state.output_dir = output_dir
            actual_cost = compute_actual_cost(input_total, output_total)
            status.success(
                f"✅ Generazione completata! {len(generated)} pagine — Costo reale: **${actual_cost} USD**"
            )

        st.session_state["is_running"] = False

    st.divider()

    if st.session_state.generated_pages:
        st.subheader("Preview e download")

        token_r = st.session_state.token_report
        actual_cost = compute_actual_cost(token_r["total_input"], token_r["total_output"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Pagine generate", len(st.session_state.generated_pages))
        col2.metric("Token totali", f"{token_r['total_input'] + token_r['total_output']:,}")
        col3.metric("Costo reale", f"${actual_cost} USD")

        st.divider()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for page in st.session_state.generated_pages:
                ptype = page.get("page_type", "page")
                city = page.get("city", "")
                service = page.get("service", "")
                if ptype == "city_page" and city:
                    fname = f"city_{city.lower().replace(' ', '_')}.json"
                elif ptype == "servizio" and service:
                    fname = f"servizio_{service.lower().replace(' ', '_')}.json"
                else:
                    fname = f"{ptype}.json"
                zf.writestr(fname, json.dumps(page, ensure_ascii=False, indent=2))

            zf.writestr(
                "_report.json",
                json.dumps(
                    {
                        "client": company_data["name"],
                        "pages": len(st.session_state.generated_pages),
                        "token_usage": token_r,
                        "cost_usd": actual_cost,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        zip_buffer.seek(0)
        safe_name = company_data["name"].lower().replace(" ", "_")
        st.download_button(
            "📦 Scarica tutti i JSON (ZIP)",
            data=zip_buffer,
            file_name=f"seo_factory_{safe_name}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )

        st.divider()
        st.subheader("Preview pagine generate")

        for page in st.session_state.generated_pages:
            ptype = page.get("page_type", "")
            city = page.get("city", "")
            service = page.get("service", "")
            label = (
                city
                if ptype == "city_page"
                else (service if ptype == "servizio" else ptype.replace("_", " ").title())
            )

            with st.expander(f"📄 {label}", expanded=False):
                seo = page.get("seo", {})
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"**Meta title:** {seo.get('meta_title', '')}")
                    st.markdown(f"**Meta description:** {seo.get('meta_description', '')}")
                    st.markdown(f"**H1:** {seo.get('h1', '')}")
                with col2:
                    st.markdown("**Schema JSON-LD:**")
                    if page.get("schema_jsonld"):
                        st.code(
                            json.dumps(page["schema_jsonld"][0], ensure_ascii=False, indent=2)[:600] + "...",
                            language="json",
                        )

                content = page.get("content", {})
                if content.get("intro") or content.get("intro_locale"):
                    st.markdown("**Intro:**")
                    st.write(content.get("intro") or content.get("intro_locale", ""))

                if page.get("faq_html"):
                    st.markdown("**FAQ HTML:**")
                    st.code(page["faq_html"][:800], language="html")

                st.markdown("**JSON completo:**")
                st.json(page)
