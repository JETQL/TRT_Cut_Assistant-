# TRT Cut Assistant

A Streamlit-based dashboard that helps media operations teams quickly determine which segments to remove in order to hit target TRT (Total Runtime) goals while respecting protected content rules.

Built for sports highlight and game recap workflows where certain innings, opens, finals, and scoring segments cannot be removed.

---

# Features

## TRT Optimization
- Calculates required time removal
- Suggests best cut combinations
- Supports preferred segment counts
- Supports “prefer under TRT” logic

## Protected Segment Rules
Automatically protects:
- OPEN segments
- FINAL segments
- Scoring innings
- T1ST
- B1ST

Users can toggle protections on/off directly in the dashboard.

---

# OCR Screenshot Support

Upload screenshots of timing sheets directly into the dashboard.

The app:
- Displays uploaded timing screenshots
- Uses OCR to extract timing text
- Attempts to auto-detect segment durations
- Allows manual correction before processing

---

# Tech Stack

- Python
- Streamlit
- OpenCV
- Tesseract OCR
- Pillow
- Pandas

---

# Installation

Install dependencies:

```bash
pip install -r requirements.txt