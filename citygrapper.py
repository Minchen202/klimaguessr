import requests
import zipfile
import io
import csv

# Download GeoNames cities dataset (cities with population > 1000)
url = "https://download.geonames.org/export/dump/cities1000.zip"
response = requests.get(url)

# Extract ZIP in memory
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    with z.open("cities1000.txt") as f:
        reader = csv.reader(io.TextIOWrapper(f, "utf-8"), delimiter="\t")
        
        cities = []
        for row in reader:
            city_name = row[1]
            country_code = row[8]
            cities.append(f"{city_name}, {country_code}")
            
            if len(cities) >= 10000:
                break

with open("cities.txt", "w", encoding="utf-8") as f:
    f.write("cities = [\n")
    for city in cities:
        f.write(f'    "{city[:-4]}",\n')
    f.write("]")