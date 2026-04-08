import requests
import time

OSM_OVERPASS = "https://overpass-api.de/api/interpreter"

CITY_SUGGESTIONS = {
    "lombardia": ["Milano", "Bergamo", "Brescia", "Monza", "Como", "Varese", "Mantova", "Cremona"],
    "veneto": ["Venezia", "Verona", "Padova", "Vicenza", "Treviso", "Belluno", "Rovigo"],
    "lazio": ["Roma", "Latina", "Frosinone", "Viterbo", "Rieti"],
    "campania": ["Napoli", "Salerno", "Caserta", "Avellino", "Benevento"],
    "piemonte": ["Torino", "Novara", "Alessandria", "Asti", "Cuneo", "Vercelli"],
    "toscana": ["Firenze", "Pisa", "Siena", "Lucca", "Arezzo", "Livorno"],
    "emilia-romagna": ["Bologna", "Modena", "Parma", "Reggio Emilia", "Ferrara", "Rimini"],
    "sicilia": ["Palermo", "Catania", "Messina", "Agrigento", "Siracusa"],
    "puglia": ["Bari", "Lecce", "Taranto", "Foggia", "Brindisi"],
    "calabria": ["Reggio Calabria", "Catanzaro", "Cosenza", "Crotone"],
    "sardegna": ["Cagliari", "Sassari", "Nuoro", "Oristano"],
    "liguria": ["Genova", "La Spezia", "Savona", "Imperia"],
    "umbria": ["Perugia", "Terni"],
    "marche": ["Ancona", "Pesaro", "Macerata", "Fermo", "Ascoli Piceno"],
    "abruzzo": ["L'Aquila", "Pescara", "Chieti", "Teramo"],
    "basilicata": ["Potenza", "Matera"],
    "molise": ["Campobasso", "Isernia"],
    "trentino": ["Trento", "Bolzano", "Rovereto"],
    "friuli": ["Trieste", "Udine", "Pordenone", "Gorizia"],
    "valle d'aosta": ["Aosta"],
}

REGION_MAP = {
    "milano": "lombardia", "bergamo": "lombardia", "brescia": "lombardia",
    "monza": "lombardia", "como": "lombardia", "varese": "lombardia",
    "venezia": "veneto", "verona": "veneto", "padova": "veneto", "vicenza": "veneto",
    "roma": "lazio", "latina": "lazio", "frosinone": "lazio",
    "napoli": "campania", "salerno": "campania", "caserta": "campania",
    "torino": "piemonte", "novara": "piemonte", "cuneo": "piemonte",
    "firenze": "toscana", "pisa": "toscana", "siena": "toscana",
    "bologna": "emilia-romagna", "modena": "emilia-romagna", "parma": "emilia-romagna",
    "palermo": "sicilia", "catania": "sicilia", "messina": "sicilia",
    "bari": "puglia", "lecce": "puglia", "taranto": "puglia",
    "genova": "liguria", "perugia": "umbria", "ancona": "marche",
    "trento": "trentino", "bolzano": "trentino", "trieste": "friuli", "udine": "friuli",
}

CLIMATE_DATA = {
    "lombardia": "clima continentale con estati calde e inverni freddi, frequenti nebbie padane in autunno e inverno",
    "veneto": "clima temperato con estati calde, inverni freschi e precipitazioni ben distribuite",
    "lazio": "clima mediterraneo con estati calde e secche, inverni miti con piogge moderate",
    "campania": "clima mediterraneo tipico, estati calde e siccitose, inverni miti",
    "piemonte": "clima continentale con forte escursione termica, abbondanti nevicate in montagna",
    "toscana": "clima mediterraneo con estati calde, inverni miti sulle coste e più freddi nell'entroterra",
    "emilia-romagna": "clima continentale con estati afose e umide, inverni freddi e nebbiosi",
    "sicilia": "clima mediterraneo con estati molto calde e lunghe, inverni miti",
    "puglia": "clima mediterraneo semiarido con estati torride e inverni miti",
    "calabria": "clima mediterraneo con forti contrasti tra costa e zone montane interne",
    "sardegna": "clima mediterraneo con influenza marina, estati calde e ventose",
    "liguria": "clima mediterraneo mite tutto l'anno, protetto dalla catena alpina",
    "trentino": "clima alpino con inverni rigidi e nevosi, estati fresche",
    "friuli": "clima di transizione tra continentale e mediterraneo, precipitazioni elevate",
}


def get_suggested_cities(city_list: list) -> list:
    """Suggest additional nearby cities based on the region of provided cities."""
    regions_found = set()
    for city in city_list:
        region = REGION_MAP.get(city.lower().strip())
        if region:
            regions_found.add(region)

    suggestions = []
    for region in regions_found:
        for c in CITY_SUGGESTIONS.get(region, []):
            if c not in city_list and c not in suggestions:
                suggestions.append(c)

    return suggestions[:8]


def get_osm_pois(city: str, amenity_type: str = "landmark") -> list:
    """Get real POIs from OpenStreetMap for a city."""
    queries = {
        "landmark": f"""
            [out:json][timeout:10];
            area["name"="{city}"]["boundary"="administrative"]->.searchArea;
            (
              node["tourism"="museum"](area.searchArea);
              node["tourism"="attraction"](area.searchArea);
              node["amenity"="theatre"](area.searchArea);
            );
            out 5;
        """,
        "business": f"""
            [out:json][timeout:10];
            area["name"="{city}"]["boundary"="administrative"]->.searchArea;
            (
              node["amenity"="hospital"](area.searchArea);
              node["amenity"="university"](area.searchArea);
            );
            out 3;
        """
    }

    query = queries.get(amenity_type, queries["landmark"])
    try:
        r = requests.post(OSM_OVERPASS, data={"data": query}, timeout=12)
        data = r.json()
        pois = []
        for el in data.get("elements", [])[:5]:
            name = el.get("tags", {}).get("name")
            if name:
                pois.append(name)
        return pois
    except Exception:
        return []


def get_city_context(city: str) -> dict:
    """Build a rich context dict for a city."""
    region = REGION_MAP.get(city.lower().strip(), "")
    climate = CLIMATE_DATA.get(region, "clima variabile tipico della zona")

    pois = get_osm_pois(city)
    time.sleep(0.3)

    return {
        "city": city,
        "region": region.title() if region else "",
        "climate": climate,
        "pois": pois,
        "poi_text": ", ".join(pois) if pois else f"il centro storico di {city}",
    }
