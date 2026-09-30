"""Smart Greenhouse and Ecosystem Management Console (PyQt6)



Features:

- Control Center: greenhouse name + plant selection + ideal ranges loaded from JSON

- Simulation: QTimer generates sensor readings every 3 seconds using a random walk, with water-tank tracking

- Critical Alert: blinking warning and red QSS background when readings become critical

- Controls: manual ventilation / heater / water refill / irrigation pump

- Autonomous Mode: automatic device control using tolerance bands

- Event Log: timestamped QListWidget

- Report: TXT and optional PDF export

- History: XOR + Base64 encoded JSON lines stored in performance_history.log

- Chart: historical performance scores displayed with matplotlib



Installation:

    pip install PyQt6 matplotlib reportlab

Run:

    python app.py

"""



from __future__ import annotations



import base64

import json

import math

import random

import sys

from dataclasses import dataclass

from datetime import datetime

from pathlib import Path

from typing import Dict, List, Tuple, Optional



from PyQt6.QtCore import Qt, QTimer

from PyQt6.QtGui import QFont

from PyQt6.QtWidgets import (

    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,

    QGroupBox, QHBoxLayout, QLabel, QLCDNumber, QLineEdit, QListWidget,

    QMessageBox, QPushButton, QProgressBar, QVBoxLayout, QWidget

)



from matplotlib.figure import Figure

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas



APP_DIR = Path(__file__).resolve().parent

PLANT_DB_PATH = APP_DIR / "plant_library.json"

HISTORY_LOG_PATH = APP_DIR / "performance_history.log"



_XOR_KEY = b"greenhouse-console-key-v1"





def now_str() -> str:

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")





def clamp(x: float, lo: float, hi: float) -> float:

    return max(lo, min(hi, x))





def xor_encrypt_bytes(data: bytes, key: bytes = _XOR_KEY) -> bytes:

    out = bytearray(len(data))

    for i, b in enumerate(data):

        out[i] = b ^ key[i % len(key)]

    return bytes(out)





def encrypt_line(obj: dict) -> str:

    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")

    enc = xor_encrypt_bytes(raw)

    return base64.b64encode(enc).decode("ascii")





def decrypt_line(line: str) -> Optional[dict]:

    line = line.strip()

    if not line:

        return None

    try:

        enc = base64.b64decode(line.encode("ascii"))

        raw = xor_encrypt_bytes(enc)

        return json.loads(raw.decode("utf-8"))

    except Exception:

        return None





@dataclass

class PlantProfile:

    name: str

    icon: str

    ranges: Dict[str, Tuple[float, float]]





@dataclass

class SensorSnapshot:

    t: int

    temp: float

    humidity: float

    soil: float

    light: float

    co2: float

    water: float





def load_plant_profiles(path: Path) -> Dict[str, PlantProfile]:

    if not path.exists():

        raise FileNotFoundError(f"Plant library not found: {path}")



    data = json.loads(path.read_text(encoding="utf-8"))

    profiles: Dict[str, PlantProfile] = {}

    for plant_name, payload in data.items():

        ranges = payload.get("ranges", {})

        needed = ["temp", "humidity", "soil", "light", "co2"]

        for k in needed:

            if k not in ranges or not isinstance(ranges[k], list) or len(ranges[k]) != 2:

                raise ValueError(f"Invalid format: {plant_name} -> {k} range is missing or invalid")

        profiles[plant_name] = PlantProfile(

            name=plant_name,

            icon=str(payload.get("icon", "🌿")),

            ranges={k: (float(ranges[k][0]), float(ranges[k][1])) for k in needed},

        )

    return profiles





class SensorEngine:

    def __init__(self, profile: PlantProfile):

        self.profile = profile

        r = profile.ranges

        self.temp = random.uniform(*r["temp"])

        self.humidity = random.uniform(*r["humidity"])

        self.soil = random.uniform(*r["soil"])

        self.light = random.uniform(*r["light"])

        self.co2 = random.uniform(*r["co2"])

        self.water = 100.0



        self.heater = 0.0

        self.vent = 0.0

        self.pump = 0.0



    def step(self) -> None:

        self.temp += random.uniform(-0.6, 0.6)

        self.humidity += random.uniform(-2.0, 2.0)

        self.soil += random.uniform(-1.5, 1.5)

        self.light += random.uniform(-30, 30)

        self.co2 += random.uniform(-40, 40)



        self.temp += 0.9 * self.heater

        self.humidity -= 0.8 * self.heater



        self.temp -= 0.8 * self.vent

        self.co2 -= 120 * self.vent

        self.humidity -= 0.6 * self.vent



        if self.pump > 0 and self.water > 0:

            self.soil += 4.0 * self.pump

            self.humidity += 1.2 * self.pump

            self.water -= 6.0 * self.pump



        self.temp = clamp(self.temp, -5, 60)

        self.humidity = clamp(self.humidity, 0, 100)

        self.soil = clamp(self.soil, 0, 100)

        self.light = clamp(self.light, 0, 1200)

        self.co2 = clamp(self.co2, 250, 2000)

        self.water = clamp(self.water, 0, 100)



        self.heater = max(0.0, self.heater - 0.15)

        self.vent = max(0.0, self.vent - 0.18)

        self.pump = max(0.0, self.pump - 0.25)



    def manual_heater(self):

        self.heater = clamp(self.heater + 0.9, 0, 1)



    def manual_vent(self):

        self.vent = clamp(self.vent + 0.9, 0, 1)



    def manual_water_topup(self):

        self.water = clamp(self.water + 35, 0, 100)



    def manual_irrigate(self):

        self.pump = clamp(self.pump + 1.0, 0, 1)





class HistoryDialog(QDialog):

    def __init__(self, parent: QWidget, entries: List[dict]):

        super().__init__(parent)

        self.setWindowTitle("Historical Performance Charts")

        self.resize(700, 420)



        fig = Figure()

        canvas = FigureCanvas(fig)

        ax = fig.add_subplot(111)



        scores = [e.get("score", 0) for e in entries]

        ax.plot(range(len(scores)), scores)

        ax.set_title("Historical Simulation Scores")

        ax.set_xlabel("Record Number")

        ax.set_ylabel("Score (0-100)")

        ax.grid(True, alpha=0.2)



        layout = QVBoxLayout()

        layout.addWidget(canvas)

        self.setLayout(layout)





DARK_QSS = """

QWidget { background: #121212; color: #EDEDED; }

QGroupBox { border: 1px solid #2a2a2a; margin-top: 10px; border-radius: 8px; }

QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px 0 4px; }

QPushButton { background: #1f1f1f; border: 1px solid #333; padding: 8px 10px; border-radius: 8px; }

QPushButton:hover { background: #242424; }

QPushButton:checked { background: #2b2b2b; border: 1px solid #555; }

QLineEdit, QComboBox { background: #1a1a1a; border: 1px solid #333; padding: 6px; border-radius: 6px; }

QListWidget { background: #101010; border: 1px solid #333; border-radius: 8px; }

QProgressBar { border: 1px solid #333; border-radius: 8px; text-align: center; }

QProgressBar::chunk { background-color: #2b7cff; border-radius: 8px; }

"""



LIGHT_QSS = """

QWidget { background: #FAFAFA; color: #111; }

QGroupBox { border: 1px solid #ddd; margin-top: 10px; border-radius: 8px; }

QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px 0 4px; }

QPushButton { background: #ffffff; border: 1px solid #ccc; padding: 8px 10px; border-radius: 8px; }

QPushButton:hover { background: #f5f5f5; }

QPushButton:checked { background: #efefef; border: 1px solid #aaa; }

QLineEdit, QComboBox { background: #ffffff; border: 1px solid #ccc; padding: 6px; border-radius: 6px; }

QListWidget { background: #ffffff; border: 1px solid #ccc; border-radius: 8px; }

QProgressBar { border: 1px solid #ccc; border-radius: 8px; text-align: center; }

QProgressBar::chunk { background-color: #2b7cff; border-radius: 8px; }

"""



CRITICAL_BG_QSS = "QWidget { background: #3a0000; color: #ffefef; }"





class ControlCenter(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("Smart Greenhouse Control Center")

        self.resize(720, 360)



        try:

            self.profiles = load_plant_profiles(PLANT_DB_PATH)

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Could not read the plant library.\n\nDetails:\n{e}")

            self.profiles = {}



        title = QLabel("Next-Generation Smart Greenhouse Control Center")

        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))



        self.name_in = QLineEdit()

        self.name_in.setPlaceholderText("Greenhouse name (e.g., My Greenhouse)")



        self.plant_combo = QComboBox()

        self.plant_combo.addItems(list(self.profiles.keys()) if self.profiles else ["(no plants available)"])



        self.preview = QLabel("🌿")

        self.preview.setFont(QFont("Arial", 26))

        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)



        self.ref_label = QLabel("")

        self.ref_label.setWordWrap(True)



        self.plant_combo.currentTextChanged.connect(self._update_preview)



        self.start_btn = QPushButton("Start System")

        self.start_btn.clicked.connect(self._start)



        form = QFormLayout()

        form.addRow("Greenhouse Name:", self.name_in)

        form.addRow("Plant Type:", self.plant_combo)



        box = QGroupBox("Configuration")

        box.setLayout(form)



        right = QVBoxLayout()

        right.addWidget(QLabel("Selected Plant"))

        right.addWidget(self.preview)

        right.addWidget(QLabel("Ideal Conditions (Reference)"))

        right.addWidget(self.ref_label, 1)



        main = QHBoxLayout()

        main.addWidget(box, 2)

        main.addLayout(right, 1)



        outer = QVBoxLayout()

        outer.addWidget(title)

        outer.addLayout(main)

        outer.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignRight)



        self.setLayout(outer)

        self._update_preview(self.plant_combo.currentText())



    def _update_preview(self, plant_name: str):

        p = self.profiles.get(plant_name)

        if not p:

            self.preview.setText("🌿")

            self.ref_label.setText("")

            return

        self.preview.setText(p.icon)

        r = p.ranges

        self.ref_label.setText(

            f"Temperature: {r['temp'][0]}–{r['temp'][1]} °C\n"

            f"Humidity: {r['humidity'][0]}–{r['humidity'][1]} %\n"

            f"Soil Moisture: {r['soil'][0]}–{r['soil'][1]} %\n"

            f"Light: {r['light'][0]}–{r['light'][1]} lx\n"

            f"CO₂: {r['co2'][0]}–{r['co2'][1]} ppm"

        )



    def _start(self):

        name = self.name_in.text().strip()

        plant = self.plant_combo.currentText().strip()

        if not name:

            QMessageBox.warning(self, "Missing Information", "Please enter a greenhouse name.")

            return

        if plant not in self.profiles:

            QMessageBox.warning(self, "Missing Information", "Please select a valid plant.")

            return



        self.main = MainConsole(greenhouse_name=name, profile=self.profiles[plant])

        self.main.show()

        self.close()





class MainConsole(QWidget):

    def __init__(self, greenhouse_name: str, profile: PlantProfile):

        super().__init__()

        self.greenhouse_name = greenhouse_name

        self.profile = profile

        self.setWindowTitle(f"{profile.icon}  {greenhouse_name} — Smart Greenhouse Console")

        self.resize(980, 620)



        self.sim_seconds = 0

        self.engine = SensorEngine(profile)

        self.autonomous = False



        self.snapshots: List[SensorSnapshot] = []

        self.ideal_ticks = 0

        self.critical_hits = 0

        self.total_water_used = 0.0

        self.max_temp = -1e9

        self.min_humidity = 1e9



        # Set the theme state before building the UI.

        # Some labels depend on self._dark while their styles are being calculated.

        self._dark = True



        self._build_ui()

        self._apply_theme(dark=True)



        self.tick_timer = QTimer(self)

        self.tick_timer.setInterval(3000)

        self.tick_timer.timeout.connect(self._on_tick)

        self.tick_timer.start()



        self.blink_timer = QTimer(self)

        self.blink_timer.setInterval(450)

        self.blink_timer.timeout.connect(self._blink)

        self._blink_state = False



        self._log("System started. Reference values are fixed.")



    def _build_ui(self):

        header = QLabel(f"{self.profile.icon}  {self.greenhouse_name} — {self.profile.name}")

        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))



        self.time_label = QLabel("Simulation Time: 0 s")



        self.critical_label = QLabel("CRITICAL ALERT")

        self.critical_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.critical_label.setStyleSheet("padding: 8px; border-radius: 8px; font-weight: bold; background: #7a0000;")

        self.critical_label.hide()



        top_row = QHBoxLayout()

        top_row.addWidget(header, 2)

        top_row.addWidget(self.time_label, 1)

        top_row.addWidget(self.critical_label, 1)



        ref = QLabel(self._ref_text())

        ref.setWordWrap(True)

        ref_box = QGroupBox("Reference (Ideal Ranges)")

        ref_layout = QVBoxLayout()

        ref_layout.addWidget(ref)

        ref_box.setLayout(ref_layout)



        self.lcd_temp = self._mk_lcd("Temperature (°C)")

        self.lcd_hum = self._mk_lcd("Humidity (%)")

        self.lcd_soil = self._mk_lcd("Soil Moisture (%)")

        self.lcd_light = self._mk_lcd("Light (lx)")

        self.lcd_co2 = self._mk_lcd("CO₂ (ppm)")



        lcd_grid = QVBoxLayout()

        row1 = QHBoxLayout(); row2 = QHBoxLayout()

        row1.addWidget(self.lcd_temp[0]); row1.addWidget(self.lcd_hum[0]); row1.addWidget(self.lcd_soil[0])

        row2.addWidget(self.lcd_light[0]); row2.addWidget(self.lcd_co2[0])

        lcd_grid.addLayout(row1); lcd_grid.addLayout(row2)



        lcd_box = QGroupBox("Live Sensor Data")

        lcd_box.setLayout(lcd_grid)



        self.water_bar = QProgressBar()

        self.water_bar.setRange(0, 100)

        self.water_bar.setValue(int(self.engine.water))

        self.water_bar.setFormat("Water Tank: %p%")

        water_box = QGroupBox("Water System")

        wlay = QVBoxLayout()

        wlay.addWidget(self.water_bar)

        water_box.setLayout(wlay)



        self.btn_vent = QPushButton("Manual Ventilation")

        self.btn_heat = QPushButton("Activate Heater")

        self.btn_irrig = QPushButton("Irrigation Pump")

        self.btn_topup = QPushButton("Refill Water Tank")



        self.btn_vent.clicked.connect(self._manual_vent)

        self.btn_heat.clicked.connect(self._manual_heat)

        self.btn_irrig.clicked.connect(self._manual_irrigate)

        self.btn_topup.clicked.connect(self._manual_topup)



        self.chk_auto = QCheckBox("Autonomous Mode")

        self.chk_auto.stateChanged.connect(self._toggle_autonomous)



        self.btn_report = QPushButton("Export Performance Report")

        self.btn_report.clicked.connect(self._export_report)



        self.btn_history = QPushButton("Performance History")

        self.btn_history.clicked.connect(self._show_history)



        self.btn_theme = QPushButton("Theme: Dark/Light")

        self.btn_theme.setCheckable(True)

        self.btn_theme.clicked.connect(self._toggle_theme)



        self.btn_pause = QPushButton("Pause Simulation")

        self.btn_pause.clicked.connect(self._toggle_simulation)



        # Device status panel

        self.lbl_heater = QLabel("Heater: Off")

        self.lbl_vent = QLabel("Ventilation: Off")

        self.lbl_pump = QLabel("Pump: Off")

        self.lbl_heater.setStyleSheet("color: #777;")

        self.lbl_vent.setStyleSheet("color: #777;")

        self.lbl_pump.setStyleSheet("color: #777;")



        status_box = QGroupBox("Device Status")

        s_lay = QVBoxLayout()

        s_lay.addWidget(self.lbl_heater)

        s_lay.addWidget(self.lbl_vent)

        s_lay.addWidget(self.lbl_pump)

        status_box.setLayout(s_lay)



        controls = QVBoxLayout()

        for w in [self.btn_vent, self.btn_heat, self.btn_irrig, self.btn_topup]:

            controls.addWidget(w)

        controls.addSpacing(8)

        controls.addWidget(self.chk_auto)

        controls.addWidget(self.btn_pause)

        controls.addSpacing(10)

        controls.addWidget(status_box)

        controls.addSpacing(10)

        controls.addWidget(self.btn_report)

        controls.addWidget(self.btn_history)

        controls.addWidget(self.btn_theme)

        controls.addStretch(1)



        controls_box = QGroupBox("Control Panel")

        controls_box.setLayout(controls)



        self.log_list = QListWidget()

        log_box = QGroupBox("Event Log")

        log_layout = QVBoxLayout()

        log_layout.addWidget(self.log_list)

        log_box.setLayout(log_layout)



        mid = QHBoxLayout()

        left = QVBoxLayout()

        left.addWidget(ref_box)

        left.addWidget(lcd_box, 1)

        left.addWidget(water_box)



        mid.addLayout(left, 3)

        mid.addWidget(controls_box, 1)



        root = QVBoxLayout()

        root.addLayout(top_row)

        root.addLayout(mid, 2)

        root.addWidget(log_box, 2)

        self.setLayout(root)



        self._refresh_displays()

        self._update_device_status()



    def _mk_lcd(self, title: str):

        box = QGroupBox(title)

        lcd = QLCDNumber()

        lcd.setDigitCount(7)

        lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)

        lay = QVBoxLayout()

        lay.addWidget(lcd)

        box.setLayout(lay)

        return box, lcd



    def _ref_text(self) -> str:

        r = self.profile.ranges

        return (

            f"Temperature: {r['temp'][0]}–{r['temp'][1]} °C\n"

            f"Humidity: {r['humidity'][0]}–{r['humidity'][1]} %\n"

            f"Soil Moisture: {r['soil'][0]}–{r['soil'][1]} %\n"

            f"Light: {r['light'][0]}–{r['light'][1]} lx\n"

            f"CO₂: {r['co2'][0]}–{r['co2'][1]} ppm"

        )



    def _apply_theme(self, dark: bool):

        self._dark = dark

        self.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)



    def _toggle_theme(self):

        self._apply_theme(dark=not getattr(self, "_dark", True))

        self._log(f"Theme changed: {'Dark' if self._dark else 'Light'}")



    def _set_critical_visual(self, critical: bool):

        if critical:

            self.setStyleSheet((DARK_QSS if self._dark else LIGHT_QSS) + CRITICAL_BG_QSS)

        else:

            self.setStyleSheet(DARK_QSS if self._dark else LIGHT_QSS)



    def _log(self, msg: str):

        self.log_list.insertItem(0, f"[{now_str()}] {msg}")



    def _on_tick(self):

        self.sim_seconds += 3

        self.time_label.setText(f"Simulation Time: {self.sim_seconds} s")



        water_before = self.engine.water

        self.engine.step()

        water_after = self.engine.water

        if water_after < water_before:

            self.total_water_used += (water_before - water_after)



        if self.autonomous:

            self._autonomous_control()



        snap = SensorSnapshot(

            t=self.sim_seconds,

            temp=self.engine.temp,

            humidity=self.engine.humidity,

            soil=self.engine.soil,

            light=self.engine.light,

            co2=self.engine.co2,

            water=self.engine.water,

        )

        self.snapshots.append(snap)



        self.max_temp = max(self.max_temp, snap.temp)

        self.min_humidity = min(self.min_humidity, snap.humidity)



        if self._is_ideal(snap):

            self.ideal_ticks += 1

        critical = self._is_critical(snap)

        if critical:

            self.critical_hits += 1



        self._update_alert(critical)

        self._refresh_displays()

        self._update_device_status()



    def _refresh_displays(self):

        self.lcd_temp[1].display(f"{self.engine.temp:0.1f}")

        self.lcd_hum[1].display(f"{self.engine.humidity:0.1f}")

        self.lcd_soil[1].display(f"{self.engine.soil:0.1f}")

        self.lcd_light[1].display(f"{self.engine.light:0.0f}")

        self.lcd_co2[1].display(f"{self.engine.co2:0.0f}")

        self.water_bar.setValue(int(self.engine.water))



    def _update_alert(self, critical: bool):

        if critical:

            if not self.blink_timer.isActive():

                self.critical_label.show()

                self.blink_timer.start()

            self._set_critical_visual(True)

        else:

            if self.blink_timer.isActive():

                self.blink_timer.stop()

            self.critical_label.hide()

            self._set_critical_visual(False)



    def _blink(self):

        self._blink_state = not self._blink_state

        self.critical_label.setVisible(self._blink_state)



    def _is_ideal(self, s: SensorSnapshot) -> bool:

        r = self.profile.ranges

        return (

            r["temp"][0] <= s.temp <= r["temp"][1] and

            r["humidity"][0] <= s.humidity <= r["humidity"][1] and

            r["soil"][0] <= s.soil <= r["soil"][1] and

            r["light"][0] <= s.light <= r["light"][1] and

            r["co2"][0] <= s.co2 <= r["co2"][1]

        )



    def _is_critical(self, s: SensorSnapshot) -> bool:

        r = self.profile.ranges

        def outside_critical(val: float, lo: float, hi: float) -> bool:

            width = (hi - lo)

            tol = max(1e-6, 0.35 * width)

            return val < (lo - tol) or val > (hi + tol)

        return (

            outside_critical(s.temp, *r["temp"]) or

            outside_critical(s.humidity, *r["humidity"]) or

            outside_critical(s.soil, *r["soil"]) or

            outside_critical(s.light, *r["light"]) or

            outside_critical(s.co2, *r["co2"])

        )



    def _toggle_autonomous(self, state: int):

        self.autonomous = (state == Qt.CheckState.Checked.value)

        self._log(f"Autonomous mode: {'On' if self.autonomous else 'Off'}")



    def _autonomous_control(self):

        r = self.profile.ranges

        def control_level(val: float, lo: float, hi: float) -> float:

            if lo <= val <= hi:

                return 0.0

            gap = (lo - val) if val < lo else (val - hi)

            width = max(1.0, hi - lo)

            return clamp(gap / (0.8 * width), 0.0, 1.0)



        vent_need = control_level(self.engine.temp, *r["temp"])

        heat_need = control_level(self.engine.temp, *r["temp"]) if self.engine.temp < r["temp"][0] else 0.0

        soil_need = control_level(self.engine.soil, *r["soil"]) if self.engine.soil < r["soil"][0] else 0.0

        co2_need = control_level(self.engine.co2, *r["co2"])



        self.engine.vent = clamp(max(self.engine.vent, max(vent_need, co2_need)), 0, 1)

        self.engine.heater = clamp(max(self.engine.heater, heat_need), 0, 1)



        if self.engine.water <= 3:

            soil_need = 0.0

        self.engine.pump = clamp(max(self.engine.pump, soil_need), 0, 1)



        if self.engine.vent > 0.6:

            self._log("Autonomous: temperature/CO₂ deviation → ventilation activated")

        if self.engine.heater > 0.6:

            self._log("Autonomous: low temperature → heater activated")

        if self.engine.pump > 0.6:

            self._log("Autonomous: dry soil → irrigation pump activated")



    def _manual_vent(self):

        self.engine.manual_vent()

        self._log("Manual ventilation activated")



    def _manual_heat(self):

        self.engine.manual_heater()

        self._log("Manual heater activated")



    def _manual_irrigate(self):

        if self.engine.water <= 2:

            self._log("Irrigation requested, but the water tank is too low")

            return

        self.engine.manual_irrigate()

        self._log("Irrigation pump activated briefly")



    def _manual_topup(self):

        before = self.engine.water

        self.engine.manual_water_topup()

        after = self.engine.water

        self._log(f"Water refill: tank {before:0.0f}% → {after:0.0f}%")



    def _compute_score(self):

        ticks = max(1, len(self.snapshots))

        ideal_ratio = self.ideal_ticks / ticks

        base = int(round(ideal_ratio * 100))

        penalty = self.critical_hits * 5

        raw_score = clamp(base - penalty, 0, 100)



        grade_scale = {9: "A", 8: "B", 7: "C", 6: "D"}

        bucket = int(math.floor(raw_score / 10))

        grade = grade_scale.get(bucket, "F")

        if raw_score == 100:

            grade = "A+"

        info = {"score": int(raw_score), "grade": grade, "ideal_ratio": ideal_ratio,

                "critical_hits": self.critical_hits, "ticks": ticks}

        return int(raw_score), grade, info



    def _build_report_text(self, score: int, grade: str, info: dict) -> str:

        return (

            "SMART GREENHOUSE PERFORMANCE REPORT\n"

            "========================\n"

            f"Greenhouse: {self.greenhouse_name}\n"

            f"Plant: {self.profile.name}\n"

            f"Date: {now_str()}\n\n"

            "SUMMARY\n"

            "----\n"

            f"Simulation duration: {self.sim_seconds} s\n"

            f"Total measurements: {info['ticks']}\n"

            f"Ideal-condition ratio: {info['ideal_ratio']*100:0.1f}%\n"

            f"Critical events: {info['critical_hits']}\n\n"

            "STATISTICS\n"

            "------------\n"

            f"Maximum temperature: {self.max_temp:0.1f} °C\n"

            f"Minimum humidity: {self.min_humidity:0.1f} %\n"

            f"Total water used: {self.total_water_used:0.1f} % (tank-percentage based)\n\n"

            "SCORING\n"

            "--------\n"

            f"Final score: {score}/100\n"

            f"Greenhouse Performance Grade: {grade}\n\n"

            "LAST 10 MEASUREMENTS (raw data)\n"

            "----------------------\n"

            f"{self._last10_table()}"

        )



    def _export_pdf(self, path: str, report_text: str):

        try:

            from reportlab.lib.pagesizes import A4

            from reportlab.pdfgen import canvas

        except Exception as e:

            raise RuntimeError("reportlab is not installed. Choose TXT output or install reportlab for PDF export.") from e



        c = canvas.Canvas(path, pagesize=A4)

        width, height = A4

        x, y = 50, height - 60

        c.setFont("Helvetica", 11)

        for line in report_text.splitlines():

            c.drawString(x, y, line)

            y -= 16

            if y < 60:

                c.showPage()

                c.setFont("Helvetica", 11)

                y = height - 60

        c.save()



    def _append_history(self, score: int, grade: str, info: dict):

        entry = {

            "ended_at": now_str(),

            "greenhouse": self.greenhouse_name,

            "plant": self.profile.name,

            "score": score,

            "grade": grade,

            "ideal_ratio": info["ideal_ratio"],

            "critical_hits": info["critical_hits"],

            "duration_s": self.sim_seconds,

        }

        line = encrypt_line(entry)

        with open(HISTORY_LOG_PATH, "a", encoding="utf-8") as f:

            f.write(line + "\n")



    def _read_history(self) -> List[dict]:

        if not HISTORY_LOG_PATH.exists():

            return []

        entries: List[dict] = []

        for line in HISTORY_LOG_PATH.read_text(encoding="utf-8").splitlines():

            obj = decrypt_line(line)

            if obj:

                entries.append(obj)

        return entries



    def _export_report(self):

        if not self.snapshots:

            QMessageBox.information(self, "Information", "No data yet. Wait for a few simulation updates.")

            return



        score, grade, info = self._compute_score()

        report = self._build_report_text(score, grade, info)



        path, _ = QFileDialog.getSaveFileName(

            self, "Save Report", str(APP_DIR / "greenhouse_report.txt"),

            "Text (*.txt);;PDF (*.pdf)"

        )

        if not path:

            return



        try:

            if path.lower().endswith(".pdf"):

                self._export_pdf(path, report)

            else:

                Path(path).write_text(report, encoding="utf-8")

            self._log(f"Report exported: {Path(path).name}")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Could not write the report.\n\nDetails:\n{e}")

            return



        try:

            self._append_history(score, grade, info)

        except Exception as e:

            self._log(f"Could not write history record: {e}")



        QMessageBox.information(self, "Done", "Report created and saved.")



    def _show_history(self):

        entries = self._read_history()

        if not entries:

            QMessageBox.information(self, "Information", "No history records found. A report may not have been generated yet.")

            return

        dlg = HistoryDialog(self, entries)

        dlg.exec()



        # ---------- Simulation control ----------

    def _toggle_simulation(self):

        """Pause or resume the simulation."""

        if self.tick_timer.isActive():

            self.tick_timer.stop()

            if self.blink_timer.isActive():

                self.blink_timer.stop()

                self.critical_label.hide()

                self._set_critical_visual(False)

            self.btn_pause.setText("Resume Simulation")

            self._log("Simulation paused.")

        else:

            self.tick_timer.start()

            self.btn_pause.setText("Pause Simulation")

            self._log("Simulation resumed.")



    # ---------- Device status ----------

    def _update_device_status(self):

        """Display the current device state based on its 0..1 intensity level."""

        def on_off(level: float) -> str:

            return "On" if level >= 0.55 else ("Partial" if level >= 0.15 else "Off")



        self.lbl_heater.setText(f"Heater: {on_off(self.engine.heater)}")

        self.lbl_vent.setText(f"Ventilation: {on_off(self.engine.vent)}")

        self.lbl_pump.setText(f"Pump: {on_off(self.engine.pump)}")



        # Subtle status emphasis that works with either theme

        def style_for(level: float) -> str:

            if level >= 0.55:

                return "font-weight: bold;"

            if level >= 0.15:

                return "font-weight: normal;"

            return "color: #777;" if self._dark else "color: #666;"



        self.lbl_heater.setStyleSheet(style_for(self.engine.heater))

        self.lbl_vent.setStyleSheet(style_for(self.engine.vent))

        self.lbl_pump.setStyleSheet(style_for(self.engine.pump))



    # ---------- Mini table for reports ----------

    def _last10_table(self) -> str:

        last = self.snapshots[-10:]

        if not last:

            return "(no records)\n"

        header = "t(s) | temp | humidity | soil | light | co2 | water\n"

        header += "-" * 52 + "\n"

        lines = []

        for s in last:

            lines.append(

                f"{s.t:>4} | {s.temp:>4.1f} | {s.humidity:>4.1f} | {s.soil:>6.1f} | {s.light:>4.0f} | {s.co2:>4.0f} | {s.water:>3.0f}"

            )

        return header + "\n".join(lines) + "\n"





def main():

    app = QApplication(sys.argv)

    if not PLANT_DB_PATH.exists():

        QMessageBox.critical(None, "Error", f"plant_library.json not found:\n{PLANT_DB_PATH}")

        sys.exit(1)

    w = ControlCenter()

    w.show()

    sys.exit(app.exec())



if __name__ == "__main__":

    main()
