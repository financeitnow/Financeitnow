# Car Dealership Scraper

This project is a web scraper designed to collect vehicle listings and dealer information from a car dealership website. It gathers data on cars and their respective dealers, storing the information in JSON files for easy access and analysis.

## Project Structure

```
car-dealership-scraper
├── src
│   ├── main.py          # Entry point of the application
│   ├── scraper.py       # Contains the Scraper class for fetching and parsing data
│   ├── utils.py         # Utility functions for data cleaning and saving
│   └── __init__.py      # Marks the directory as a Python package
├── data
│   ├── dealers.json     # JSON file storing dealer information
│   └── cars.json        # JSON file storing car listings linked to dealers
├── requirements.txt      # Lists project dependencies
└── README.md             # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd car-dealership-scraper
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the scraper, execute the following command:
```
python src/main.py
```

This will initiate the scraping process, collect vehicle listings and dealer information, and save the results in `data/dealers.json` and `data/cars.json`.

## Scraping Process

The scraper navigates through the dealership website, handling pagination and extracting relevant data such as:
- Dealer names and contact information
- Vehicle details including make, model, price, and images

The collected data is then structured and saved in JSON format for further analysis or use.