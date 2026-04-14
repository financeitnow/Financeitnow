import json
import os
import requests
from extract_car_data import extract_car_data

def main():
    # Use the correct data directory at the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dealers_file = os.path.join(base_dir, "data", "dealers.json")
    cars_file = os.path.join(base_dir, "data", "cars.json")

    # Load dealers
    with open(dealers_file, "r") as f:
        dealers = json.load(f)

    all_cars = []
    for dealer in dealers:
        stock_url = dealer.get("stockURL")
        if not stock_url:
            continue
        print(f"Fetching cars for dealer: {dealer['dealer_name']} ({stock_url})")
        response = requests.get(stock_url)
        if response.status_code == 200:
            car_list = extract_car_data(response.text)
            # Optionally, add dealer_id to each car
            for car in car_list:
                car["dealer_id"] = dealer["dealer_id"]
            all_cars.extend(car_list)
        else:
            print(f"Failed to fetch stock page for {dealer['dealer_name']}")

    # Save all cars to cars.json
    os.makedirs(os.path.dirname(cars_file), exist_ok=True)
    with open(cars_file, "w", encoding="utf-8") as f:
        json.dump(all_cars, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(all_cars)} cars in total.")

if __name__ == "__main__":
    main()