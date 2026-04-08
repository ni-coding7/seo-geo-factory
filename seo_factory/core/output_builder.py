import json
import os
from datetime import datetime
from schemas.generators import (
    local_business_schema, faq_schema, service_schema,
    organization_schema, breadcrumb_schema, schema_to_html_tag
)


def build_faq_html(faqs: list) -> str:
    """Generate SEO-optimized FAQ HTML block."""
    if not faqs:
        return ""
    items = ""
    for faq in faqs:
        q = faq.get("question", "")
        a = faq.get("answer", "")
        items += f"""
  <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{q}</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">{a}</p>
    </div>
  </div>"""

    return f'<div class="faq-container" itemscope itemtype="https://schema.org/FAQPage">{items}\n</div>'


def assemble_page_output(
    page_type: str,
    content: dict,
    company: dict,
    city: str = None,
    service_name: str = None,
) -> dict:
    """Assemble complete page output with content + JSON-LD schemas."""

    faqs = content.get("faqs", [])
    website = company.get("website", "").rstrip("/")

    schemas = []

    if page_type == "home":
        schemas.append(local_business_schema(company, "home", city))
        if faqs:
            schemas.append(faq_schema(faqs))
        breadcrumb = breadcrumb_schema([
            {"name": "Home", "url": website + "/"}
        ])
        schemas.append(breadcrumb)

    elif page_type == "chi_siamo":
        schemas.append(organization_schema(company))
        if faqs:
            schemas.append(faq_schema(faqs))
        schemas.append(breadcrumb_schema([
            {"name": "Home", "url": website + "/"},
            {"name": "Chi siamo", "url": website + "/chi-siamo/"}
        ]))

    elif page_type == "servizio" and service_name:
        schemas.append(service_schema(company, service_name, city))
        if faqs:
            schemas.append(faq_schema(faqs))
        slug = service_name.lower().replace(" ", "-")
        schemas.append(breadcrumb_schema([
            {"name": "Home", "url": website + "/"},
            {"name": "Servizi", "url": website + "/servizi/"},
            {"name": service_name, "url": website + f"/servizi/{slug}/"}
        ]))

    elif page_type == "faq":
        if faqs:
            schemas.append(faq_schema(faqs))
        schemas.append(breadcrumb_schema([
            {"name": "Home", "url": website + "/"},
            {"name": "FAQ", "url": website + "/faq/"}
        ]))

    elif page_type == "city_page" and city:
        schemas.append(local_business_schema(company, "city", city))
        if faqs:
            schemas.append(faq_schema(faqs))
        city_slug = city.lower().replace(" ", "-")
        service_label = service_name or company.get("services", ["Servizi"])[0]
        schemas.append(breadcrumb_schema([
            {"name": "Home", "url": website + "/"},
            {"name": service_label, "url": website + f"/{service_label.lower().replace(' ','-')}/"},
            {"name": city, "url": website + f"/{service_label.lower().replace(' ','-')}/{city_slug}/"}
        ]))

    schema_tags = "\n".join(schema_to_html_tag(s) for s in schemas)

    return {
        "page_type": page_type,
        "city": city,
        "service": service_name,
        "generated_at": datetime.now().isoformat(),
        "seo": {
            "meta_title": content.get("meta_title", ""),
            "meta_description": content.get("meta_description", ""),
            "h1": content.get("h1", ""),
        },
        "content": content,
        "faq_html": build_faq_html(faqs),
        "schema_jsonld": schemas,
        "schema_html_tags": schema_tags,
    }


def save_client_output(client_name: str, pages: list, token_report: dict) -> str:
    """Save all pages to output directory and return the path."""
    safe_name = client_name.lower().replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = os.path.join("output", f"{safe_name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    for page in pages:
        ptype = page.get("page_type", "page")
        city = page.get("city", "")
        service = page.get("service", "")

        if ptype == "city_page" and city:
            filename = f"city_{city.lower().replace(' ','_')}.json"
        elif ptype == "servizio" and service:
            filename = f"servizio_{service.lower().replace(' ','_')}.json"
        else:
            filename = f"{ptype}.json"

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(page, f, ensure_ascii=False, indent=2)

    report_path = os.path.join(output_dir, "_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "client": client_name,
            "generated_at": datetime.now().isoformat(),
            "total_pages": len(pages),
            "token_usage": token_report,
            "cost_estimate_usd": round(
                (token_report.get("total_input", 0) * 0.00000025 +
                 token_report.get("total_output", 0) * 0.00000125), 4
            )
        }, f, ensure_ascii=False, indent=2)

    return output_dir
