import requests
import json
import time
from collections import defaultdict

# 1. Definiere die Orte, deren Koordinaten gefunden werden müssen
CITY_NAMES = [
    "Berlin",
    "Hamburg",
    "München",
    "Köln",
    "Frankfurt am Main",
    "Stuttgart",
    "Düsseldorf",
    "Dortmund",
    "Essen",
    "Leipzig",
    "Bremen",
    "Dresden",
    "Hannover",
    "Nürnberg",
    "Duisburg",
    "Bochum",
    "Wuppertal",
    "Bielefeld",
    "Bonn",
    "Münster",
    "Paris",
    "Lyon",
    "Marseille",
    "Toulouse",
    "Nice",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Bordeaux",
    "Lille",
    "London",
    "Manchester",
    "Birmingham",
    "Liverpool",
    "Leeds",
    "Sheffield",
    "Bristol",
    "Nottingham",
    "Leicester",
    "Oxford",
    "Madrid",
    "Barcelona",
    "Valencia",
    "Sevilla",
    "Zaragoza",
    "Malaga",
    "Murcia",
    "Palma",
    "Bilbao",
    "Granada",
    "Rome",
    "Milan",
    "Naples",
    "Turin",
    "Palermo",
    "Genoa",
    "Bologna",
    "Florence",
    "Venice",
    "Verona",
    "Vienna",
    "Graz",
    "Linz",
    "Salzburg",
    "Innsbruck",
    "Klagenfurt",
    "Zurich",
    "Geneva",
    "Basel",
    "Bern",
    "Lausanne",
    "Lucerne",
    "Amsterdam",
    "Rotterdam",
    "The Hague",
    "Utrecht",
    "Eindhoven",
    "Groningen",
    "Brussels",
    "Antwerp",
    "Ghent",
    "Bruges",
    "Liège",
    "Luxembourg",
    "Copenhagen",
    "Aarhus",
    "Odense",
    "Aalborg",
    "Stockholm",
    "Gothenburg",
    "Malmö",
    "Uppsala",
    "Västerås",
    "Oslo",
    "Bergen",
    "Trondheim",
    "Stavanger",
    "Tromsø",
    "Helsinki",
    "Espoo",
    "Tampere",
    "Turku",
    "Oulu",
    "Reykjavik",
    "Dublin",
    "Cork",
    "Galway",
    "Limerick",
    "Waterford",
    "Warsaw",
    "Krakow",
    "Lodz",
    "Wroclaw",
    "Poznan",
    "Gdansk",
    "Szczecin",
    "Bydgoszcz",
    "Lublin",
    "Katowice",
    "Prague",
    "Brno",
    "Ostrava",
    "Plzen",
    "Liberec",
    "Bratislava",
    "Kosice",
    "Budapest",
    "Debrecen",
    "Szeged",
    "Pecs",
    "Bucharest",
    "Cluj-Napoca",
    "Timisoara",
    "Iasi",
    "Brasov",
    "Sofia",
    "Plovdiv",
    "Varna",
    "Burgas",
    "Athens",
    "Thessaloniki",
    "Patras",
    "Heraklion",
    "Rhodes",
    "Istanbul",
    "Ankara",
    "Izmir",
    "Bursa",
    "Antalya",
    "Tel Aviv",
    "Jerusalem",
    "Haifa",
    "Beersheba",
    "Cairo",
    "Alexandria",
    "Giza",
    "Luxor",
    "Aswan",
    "Casablanca",
    "Rabat",
    "Marrakesh",
    "Fez",
    "Tangier",
    "Algiers",
    "Oran",
    "Constantine",
    "Tunis",
    "Sfax",
    "Sousse",
    "Tripoli",
    "Benghazi",
    "Lagos",
    "Abuja",
    "Ibadan",
    "Benin City",
    "Port Harcourt",
    "Accra",
    "Kumasi",
    "Takoradi",
    "Cape Coast",
    "Nairobi",
    "Mombasa",
    "Kisumu",
    "Eldoret",
    "Dar es Salaam",
    "Dodoma",
    "Arusha",
    "Mwanza",
    "Kampala",
    "Entebbe",
    "Jinja",
    "Kigali",
    "Bujumbura",
    "Addis Ababa",
    "Dire Dawa",
    "Bahir Dar",
    "Mekelle",
    "Johannesburg",
    "Cape Town",
    "Durban",
    "Pretoria",
    "Bloemfontein",
    "Gaborone",
    "Windhoek",
    "Harare",
    "Bulawayo",
    "Lusaka",
    "Ndola",
    "Maputo",
    "Beira",
    "Luanda",
    "Benguela",
    "Kinshasa",
    "Lubumbashi",
    "Brazzaville",
    "Pointe-Noire",
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "San Jose",
    "San Francisco",
    "Seattle",
    "Portland",
    "Denver",
    "Boulder",
    "Boston",
    "Cambridge",
    "Somerville",
    "Miami",
    "Orlando",
    "Tampa",
    "Atlanta",
    "Savannah",
    "Charleston",
    "Washington",
    "Baltimore",
    "Richmond",
    "Toronto",
    "Montreal",
    "Vancouver",
    "Calgary",
    "Edmonton",
    "Ottawa",
    "Quebec City",
    "Winnipeg",
    "Hamilton",
    "Mississauga",
    "Mexico City",
    "Guadalajara",
    "Monterrey",
    "Puebla",
    "Tijuana",
    "Cancun",
    "Merida",
    "Oaxaca",
    "Havana",
    "Santiago de Cuba",
    "Varadero",
    "Kingston",
    "Montego Bay",
    "Port-au-Prince",
    "Santo Domingo",
    "San Juan",
    "Bogota",
    "Medellin",
    "Cali",
    "Barranquilla",
    "Cartagena",
    "Caracas",
    "Maracaibo",
    "Valencia",
    "Barquisimeto",
    "Quito",
    "Guayaquil",
    "Cuenca",
    "Lima",
    "Arequipa",
    "Trujillo",
    "Cusco",
    "La Paz",
    "Santa Cruz",
    "Cochabamba",
    "Santiago",
    "Valparaiso",
    "Concepcion",
    "Buenos Aires",
    "Cordoba",
    "Rosario",
    "Mendoza",
    "La Plata",
    "Montevideo",
    "Punta del Este",
    "Asuncion",
    "Ciudad del Este",
    "Sao Paulo",
    "Rio de Janeiro",
    "Belo Horizonte",
    "Brasilia",
    "Salvador",
    "Recife",
    "Fortaleza",
    "Manaus",
    "Belem",
    "Curitiba",
    "Porto Alegre",
    "Florianopolis",
    "Campinas",
    "Ribeirao Preto",
    "Goiania",
    "Tokyo",
    "Yokohama",
    "Osaka",
    "Kyoto",
    "Nagoya",
    "Kobe",
    "Hiroshima",
    "Fukuoka",
    "Sapporo",
    "Sendai",
    "Seoul",
    "Busan",
    "Incheon",
    "Daegu",
    "Daejeon",
    "Beijing",
    "Shanghai",
    "Guangzhou",
    "Shenzhen",
    "Chengdu",
    "Wuhan",
    "Xi'an",
    "Hangzhou",
    "Nanjing",
    "Suzhou",
    "Hong Kong",
    "Macau",
    "Taipei",
    "Kaohsiung",
    "Taichung",
    "Bangkok",
    "Chiang Mai",
    "Phuket",
    "Pattaya",
    "Hanoi",
    "Ho Chi Minh City",
    "Da Nang",
    "Hue",
    "Singapore",
    "Kuala Lumpur",
    "Penang",
    "Johor Bahru",
    "Jakarta",
    "Bandung",
    "Surabaya",
    "Yogyakarta",
    "Denpasar",
    "Manila",
    "Cebu City",
    "Davao City",
    "Quezon City",
    "Makati",
    "Sydney",
    "Melbourne",
    "Brisbane",
    "Perth",
    "Adelaide",
    "Canberra",
    "Hobart",
    "Darwin",
    "Auckland",
    "Wellington",
    "Christchurch",
    "Hamilton",
    "Dunedin"
]


def get_coordinates(city_name):
    """
    Ruft Breitengrad und Längengrad für einen Stadtnamen über die Open-Meteo Geocoding API ab.
    """
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,  # Nur das relevanteste Ergebnis
        "language": "de",
        "format": "json"
    }
    
    try:
        response = requests.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('results'):
            result = data['results'][0]
            return {
                "name": result.get('name', city_name),
                "lat": result['latitude'],
                "lng": result['longitude']
            }
        else:
            print(f"Warnung: Keine Koordinaten für '{city_name}' gefunden.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Geocoding für '{city_name}': {e}")
        return None

# (Die Funktion get_climate_data bleibt unverändert aus der letzten Antwort)
# ... [Fügen Sie die Funktion get_climate_data(city_name, latitude, longitude) hier ein] ...
def get_climate_data(city_name, latitude, longitude):
    """
    Ruft historische monatliche Durchschnittstemperaturen und gesamten Niederschlag
    für den angegebenen Ort von der Open-Meteo API ab und formatiert sie.
    (Funktion aus der vorherigen Antwort hier einfügen)
    """
    API_URL = "https://archive-api.open-meteo.com/v1/archive"
    start_date = "2023-01-01"
    end_date = "2023-12-31"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["temperature_2m_mean", "precipitation_sum"],
        "timezone": "auto"
    }

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei {city_name}: {e}")
        return None

    # Datenverarbeitung (wie zuvor)
    monthly_data = defaultdict(lambda: {"temp_sum": 0.0, "precip_sum": 0.0, "count": 0})
    
    if 'daily' not in data: return None

    daily_times = data['daily']['time']
    daily_temps = data['daily']['temperature_2m_mean']
    daily_precips = data['daily']['precipitation_sum']

    for i, date_str in enumerate(daily_times):
        month = int(date_str[5:7])
        monthly_data[month]['temp_sum'] += daily_temps[i]
        monthly_data[month]['precip_sum'] += daily_precips[i]
        monthly_data[month]['count'] += 1

    temp_monthly_avg = []
    precip_monthly_sum = []
    
    for month in range(1, 13):
        if monthly_data[month]['count'] > 0:
            avg_temp = round(monthly_data[month]['temp_sum'] / monthly_data[month]['count'], 1)
            sum_precip = round(monthly_data[month]['precip_sum'], 1)
            temp_monthly_avg.append(avg_temp)
            precip_monthly_sum.append(sum_precip)
        else:
            temp_monthly_avg.append(0.0)
            precip_monthly_sum.append(0.0)

    result = {
        "name": city_name,
        "lat": latitude,
        "lng": longitude,
        "temp": temp_monthly_avg,
        "precip": precip_monthly_sum
    }

    return result

# --- HAUPTPROZESS FÜR DEN ABDAUF MIT GEOCDING ---

all_climate_data = []

for city_name in CITY_NAMES:
    
    # 2. Schritt: Koordinaten finden
    location_data = get_coordinates(city_name)
    
    if location_data:
        city = location_data['name']
        lat = location_data['lat']
        lng = location_data['lng']
        
        print(f"-> Verarbeite: {city} ({lat}, {lng})...")
        
        # 3. Schritt: Klimadaten abrufen
        data = get_climate_data(city, lat, lng)
        
        if data:
            all_climate_data.append(data)

# Speichere alle Daten in einer einzigen großen JSON-Datei
with open("geocoded_climate_data.json", "w") as f:
    json.dump(all_climate_data, f, indent=4)

print("\n--- Prozess abgeschlossen ---")
print(f"Daten für {len(all_climate_data)} Orte in 'geocoded_climate_data.json' gespeichert.")