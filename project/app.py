from flask import Flask, render_template, jsonify, request
from geopy.geocoders import Nominatim
import random
import folium
from folium.plugins import MarkerCluster

app = Flask(__name__)

# =============================
# Function to simulate parking spots data
# =============================
@app.route('/')
def home_page():
    return render_template('home_page.html')


@app.route('/main')
def main():
    spots = get_parking_status()
    best_distribution = genetic_algorithm(spots)

    # Create map
    base_map = folium.Map(location=[33.5138, 36.2765], zoom_start=14)
    marker_cluster = MarkerCluster().add_to(base_map)

    for spot in spots:
        color = 'green' if spot['status'] == 'available' else 'red'
        folium.CircleMarker(
            location=[spot['lat'], spot['lon']],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"Spot ID: {spot['id']}<br>Status: {spot['status']}"
        ).add_to(marker_cluster)

    # Save map to file
    map_html = "templates/map.html"
    base_map.save(map_html)

    return render_template('index.html', spots=spots, map_file="map.html")

def get_parking_status():
    base_lat, base_lon = 33.5138, 36.2765
    parking_spots = [
        {
            "id": i,
            "status": random.choice(["available", "occupied"]),
            "lat": base_lat + random.uniform(-0.005, 0.005),
            "lon": base_lon + random.uniform(-0.005, 0.005)
        }
        for i in range(10)
    ]
    return parking_spots

# ==============================
# Genetic Algorithm for Parking Spot Optimization
# ==============================

def fitness(parking_spots):
    available_count = sum([1 for spot in parking_spots if spot['status'] == 'available'])
    return available_count


def selection(population):
    selected = random.sample(population, 2)
    selected.sort(key=lambda x: fitness(x), reverse=True)
    return selected[0]


def crossover(parent1, parent2):
    crossover_point = random.randint(1, len(parent1) - 1)
    child = parent1[:crossover_point] + parent2[crossover_point:]
    return child


def mutation(parking_spots):
    mutation_point = random.randint(0, len(parking_spots) - 1)
    new_status = 'available' if parking_spots[mutation_point]['status'] == 'occupied' else 'occupied'
    parking_spots[mutation_point]['status'] = new_status
    return parking_spots


def genetic_algorithm(parking_spots, generations=100, population_size=20, mutation_rate=0.1):
    available_spots = [spot for spot in parking_spots if spot['status'] == 'available']

    if not available_spots:
        return []

    population = [random.sample(available_spots, len(available_spots)) for _ in range(population_size)]

    for generation in range(generations):
        selected_parents = [selection(population) for _ in range(population_size // 2)]

        next_generation = []
        for i in range(0, len(selected_parents), 2):
            child1 = crossover(selected_parents[i], selected_parents[i + 1])
            child2 = crossover(selected_parents[i + 1], selected_parents[i])
            next_generation.extend([child1, child2])

        for i in range(len(next_generation)):
            if random.random() < mutation_rate:
                next_generation[i] = mutation(next_generation[i])

        population = next_generation

    best_solution = max(population, key=lambda x: fitness(x))
    return best_solution

# ============================
# Geocoding to convert street name to coordinates
# ============================

def get_coordinates_from_address(address):
    geolocator = Nominatim(user_agent="parking_system")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    return None, None

@app.route('/')
def index():
    spots = get_parking_status()
    best_distribution = genetic_algorithm(spots)

    # Create map
    base_map = folium.Map(location=[33.5138, 36.2765], zoom_start=14)
    marker_cluster = MarkerCluster().add_to(base_map)

    for spot in spots:
        color = 'green' if spot['status'] == 'available' else 'red'
        folium.CircleMarker(
            location=[spot['lat'], spot['lon']],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"Spot ID: {spot['id']}<br>Status: {spot['status']}"
        ).add_to(marker_cluster)

    # Save map to file
    map_html = "templates/map.html"
    base_map.save(map_html)

    return render_template('index.html', spots=spots, map_file="map.html")

@app.route('/nearest-genetic', methods=['POST'])
def nearest_parking_genetic():
    data = request.get_json()
    user_lat = data.get('lat')
    user_lon = data.get('lon')

    if user_lat is None or user_lon is None:
        return jsonify({"message": "User location not provided."})

    spots = get_parking_status()

    # Filter only available spots
    available_spots = [spot for spot in spots if spot['status'] == 'available']

    if not available_spots:
        return jsonify({"message": "No available parking spots."})

    # Run genetic algorithm to optimize parking spots
    best_distribution = genetic_algorithm(available_spots)

    if not best_distribution:
        return jsonify({"message": "No available parking spots after optimization."})

    # Find the nearest spot
    nearest_spot = min(best_distribution, key=lambda spot: (spot['lat'] - user_lat) ** 2 + (spot['lon'] - user_lon) ** 2)

    # Include user's location as a blue marker
    base_map = folium.Map(location=[user_lat, user_lon], zoom_start=14)
    folium.Marker(
        location=[user_lat, user_lon],
        popup="Your Location",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(base_map)

    folium.Marker(
        location=[nearest_spot['lat'], nearest_spot['lon']],
        popup=f"Nearest Spot: {nearest_spot['id']}<br>Status: {nearest_spot['status']}",
        icon=folium.Icon(color='green')
    ).add_to(base_map)

    map_html = "templates/nearest_map.html"
    base_map.save(map_html)

    return jsonify(nearest_spot)

@app.route('/location', methods=['POST'])
def set_location():
    data = request.get_json()
    address = data.get('address')
    if not address:
        return jsonify({"message": "Please provide an address."})

    user_lat, user_lon = get_coordinates_from_address(address)
    if user_lat is None or user_lon is None:
        return jsonify({"message": "Address not found."})

    return jsonify({"lat": user_lat, "lon": user_lon})

if __name__ == '__main__':
    app.run(debug=True)


