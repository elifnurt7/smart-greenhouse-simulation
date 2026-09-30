# Smart Greenhouse Simulation

A Python desktop application that simulates the monitoring and management of a smart greenhouse environment. The application generates changing environmental conditions, allows manual and autonomous control of greenhouse systems, tracks performance, and produces simulation reports.

This project was originally developed as part of a university course and is presented here as part of my programming portfolio.

## Features

- Simulated sensor readings for temperature, humidity, soil moisture, light, and CO₂
- Plant-specific ideal environmental ranges
- Water tank monitoring
- Manual ventilation, heating, irrigation, and water refill controls
- Autonomous greenhouse management mode
- Critical-condition detection and visual alerts
- Timestamped event logging
- Pause and resume functionality
- Dark and light themes
- Greenhouse performance scoring
- TXT and PDF performance report export
- Historical performance tracking and visualization
- Multiple plant profiles including Cactus, Orchid, and Tomato

## Technologies

- Python
- PyQt6
- Matplotlib
- ReportLab
- JSON

## Project Structure

```text
smart-greenhouse-simulation/
├── app.py
├── plant_library.json
├── requirements.txt
├── README.md
└── .gitignore
```

### `app.py`

Contains the main application, graphical user interface, simulation engine, greenhouse controls, autonomous control system, reporting system, and performance history functionality.

### `plant_library.json`

Stores the environmental ranges used by the simulation for each supported plant, including temperature, humidity, soil moisture, light, and CO₂.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/elifnurt7/smart-greenhouse-simulation.git
cd smart-greenhouse-simulation
```

### 2. Install the dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

Run:

```bash
python app.py
```

The Smart Greenhouse Control Center will open. Enter a greenhouse name, select a plant profile, and start the simulation.

## How the Simulation Works

The application generates simulated environmental sensor readings every three seconds. These readings gradually change over time and are compared with the ideal environmental ranges of the selected plant.

The greenhouse can be managed manually using the ventilation, heater, irrigation, and water-refill controls. Autonomous Mode allows the application to respond automatically when environmental conditions move outside the desired ranges.

The system also monitors critical conditions and displays a visual warning when readings move significantly beyond the acceptable range.

## Performance Reports

The application can generate performance reports containing:

- Simulation duration
- Number of measurements
- Percentage of readings within ideal conditions
- Critical events
- Maximum temperature
- Minimum humidity
- Water usage
- Final performance score and grade
- Recent sensor readings

Reports can be exported as TXT or PDF files.

## Performance History

After a performance report is generated, the application stores a simulation summary locally in `performance_history.log`.

The Performance History feature reads these records and displays previous simulation scores using Matplotlib.

The history file is generated automatically while using the application and is not included in the repository.

## Purpose

This project demonstrates experience with Python application development, graphical user interfaces, object-oriented programming, simulation logic, JSON-based configuration, data visualization, file handling, and automated control logic.
