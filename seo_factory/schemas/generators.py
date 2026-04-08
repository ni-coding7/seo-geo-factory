import json


def local_business_schema(company: dict, page_type: str = "home", city: str = None) -> dict:
    """Generate LocalBusiness JSON-LD schema."""
    has_physical = company.get("has_physical_location", True)

    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": company["name"],
        "description": company.get("description", ""),
        "url": company.get("website", ""),
        "telephone": company.get("phone", ""),
        "email": company.get("email", ""),
        "priceRange": company.get("price_range", "€€"),
        "sameAs": company.get("social_profiles", []),
    }

    if has_physical:
        schema["address"] = {
            "@type": "PostalAddress",
            "streetAddress": company.get("address", ""),
            "addressLocality": company.get("city", ""),
            "postalCode": company.get("postal_code", ""),
            "addressCountry": "IT"
        }
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": company.get("lat", ""),
            "longitude": company.get("lng", "")
        }
    else:
        target_cities = company.get("target_cities", [])
        if city:
            schema["areaServed"] = {
                "@type": "City",
                "name": city
            }
        elif target_cities:
            schema["areaServed"] = [
                {"@type": "City", "name": c} for c in target_cities
            ]

    if company.get("opening_hours"):
        schema["openingHours"] = company["opening_hours"]

    if company.get("logo_url"):
        schema["image"] = company["logo_url"]

    return schema


def faq_schema(faqs: list) -> dict:
    """Generate FAQPage JSON-LD schema from list of {question, answer} dicts."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq["answer"]
                }
            }
            for faq in faqs
        ]
    }


def service_schema(company: dict, service_name: str, city: str = None) -> dict:
    """Generate Service JSON-LD schema."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": service_name,
        "provider": {
            "@type": "LocalBusiness",
            "name": company["name"],
            "url": company.get("website", ""),
            "telephone": company.get("phone", ""),
        },
        "areaServed": city if city else company.get("city", ""),
        "url": company.get("website", ""),
    }
    if company.get("price_range"):
        schema["offers"] = {
            "@type": "Offer",
            "priceCurrency": "EUR",
            "availability": "https://schema.org/InStock"
        }
    return schema


def breadcrumb_schema(items: list) -> dict:
    """Generate BreadcrumbList schema. items = [{'name': str, 'url': str}]"""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item["name"],
                "item": item["url"]
            }
            for i, item in enumerate(items)
        ]
    }


def organization_schema(company: dict) -> dict:
    """Generate Organization schema for About page."""
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": company["name"],
        "url": company.get("website", ""),
        "logo": company.get("logo_url", ""),
        "telephone": company.get("phone", ""),
        "email": company.get("email", ""),
        "foundingDate": company.get("founding_year", ""),
        "description": company.get("description", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": company.get("address", ""),
            "addressLocality": company.get("city", ""),
            "addressCountry": "IT"
        },
        "sameAs": company.get("social_profiles", [])
    }


def schema_to_html_tag(schema_dict: dict) -> str:
    """Wrap schema dict in a <script> tag ready for HTML injection."""
    return f'<script type="application/ld+json">\n{json.dumps(schema_dict, ensure_ascii=False, indent=2)}\n</script>'
