import streamlit as st
from itertools import combinations
import pandas as pd
import re
from PIL import Image

def to_seconds(t):
    parts = t.strip().split(":")
    if len(parts) == 4:
        h, m, s, f = map(int, parts)
    elif len(parts) == 3:
        h, m, s = map(int, parts)
    else:
        h = 0
        m, s = map(int, parts)
    return h * 3600 + m * 60 + s

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}:00"

def parse_raw_rows(raw_text):
    detected = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        timecodes = re.findall(r"\d{2}:\d{2}:\d{2}:\d{2}", line)

        if len(timecodes) >= 3:
            duration = timecodes[-1]

            if "+" in line:
                title_part = line.split("+")[0].strip()
            else:
                title_part = line.split(timecodes[0])[0].strip()

            title = re.sub(r"\s+", " ", title_part)

            if title:
                detected.append(f"{title}, {duration}")

    return "\n".join(detected)

def parse_csv(file):
    df = pd.read_csv(file)
    lines = []

    for _, row in df.iterrows():
        row_text = " ".join(str(x) for x in row.values)
        parsed = parse_raw_rows(row_text)
        if parsed:
            lines.append(parsed)

    return "\n".join(lines)

st.set_page_config(page_title="TRT Cut Assistant", layout="wide")

st.title("TRT Cut Assistant")

st.write(
    "Upload a screenshot for reference, paste timing report rows, and the app will auto-draft segments and suggest cuts."
)

screenshot = st.file_uploader(
    "Upload timing screenshot for reference",
    type=["png", "jpg", "jpeg"]
)

if screenshot:
    image = Image.open(screenshot)
    st.image(image, caption="Timing Screenshot Reference", use_container_width=True)

current_trt = st.text_input("Current TRT", "02:25:39:00")
target_trt = st.text_input("Target TRT", "02:01:45:00")
desired_segments = st.number_input("Desired Kept Segments", min_value=1, value=14)
prefer_under = st.checkbox("Prefer Staying Under TRT", value=False)

st.subheader("Protection Rules")

protect_open = st.checkbox("Protect OPEN", value=True)
protect_final = st.checkbox("Protect FINAL", value=True)
protect_scoring = st.checkbox("Protect Scoring Segments", value=True)
protect_t1st = st.checkbox("Protect T1ST", value=True)
protect_b1st = st.checkbox("Protect B1ST", value=True)

st.subheader("Timing Intake")

csv_file = st.file_uploader(
    "Optional: Upload CSV timing export",
    type=["csv"]
)

raw_table = st.text_area(
    "Paste timing report rows here",
    """OPEN SF|ARI +BASFG052026AMAH+ 00:00:37:00 00:02:29:00 00:01:52:00
T1ST 1|0 +BASFG052026AMCH+ 00:00:39:20 00:08:18:20 00:07:39:00
B1ST 1|1 +BASFG052026AMDH+ 00:00:36:00 00:06:28:00 00:05:52:00
T2ND 2|1 +BASFG052026AMEH+ 00:00:38:00 00:09:27:00 00:08:49:00
B2ND +BASFG052026AMFH+ 00:00:36:15 00:05:53:15 00:05:17:00
T3RD +BASFG052026AMGH+ 00:00:39:00 00:05:25:00 00:04:46:00
B3RD 2|3 +BASFG052026AMHH+ 00:00:39:00 00:09:50:00 00:09:11:00
T4TH 3|3 +BASFG052026AMIH+ 00:00:36:00 00:10:51:00 00:10:15:00
B4TH +BASFG052026AMJH+ 00:00:40:00 00:06:59:00 00:06:19:00
FINAL, 00:05:59:00""",
    height=220
)

auto_segments = ""

if csv_file:
    auto_segments = parse_csv(csv_file)
elif raw_table.strip():
    auto_segments = parse_raw_rows(raw_table)

st.subheader("Detected Segment List")
st.write("Review/edit this list before running cuts.")

segment_input = st.text_area(
    "Segments",
    auto_segments,
    height=300
)

if st.button("Find Best Cuts"):
    current_seconds = to_seconds(current_trt)
    target_seconds = to_seconds(target_trt)
    remove_needed = current_seconds - target_seconds

    segments = []
    protected_keywords = []

    if protect_open:
        protected_keywords.append("OPEN")
    if protect_final:
        protected_keywords.append("FINAL")
    if protect_t1st:
        protected_keywords.append("T1ST")
    if protect_b1st:
        protected_keywords.append("B1ST")

    for line in segment_input.splitlines():
        if not line.strip():
            continue

        try:
            if "," in line:
                title, duration = [x.strip() for x in line.split(",", 1)]
            else:
                parsed_line = parse_raw_rows(line)
                if not parsed_line:
                    st.error(f"Could not read line: {line}")
                    continue
                title, duration = [x.strip() for x in parsed_line.split(",", 1)]

            title_upper = title.upper()

            if any(keyword in title_upper for keyword in protected_keywords):
                rule = "keep"
            elif protect_scoring and "|" in title_upper:
                rule = "keep"
            else:
                rule = "cuttable"

            segments.append({
                "title": title,
                "duration": duration,
                "seconds": to_seconds(duration),
                "rule": rule
            })

        except Exception as e:
            st.error(f"Problem reading line: {line} — {e}")

    cuttable = [s for s in segments if s["rule"] == "cuttable"]
    protected = [s for s in segments if s["rule"] == "keep"]

    total_segments = len(segments)
    results = []

    for r in range(1, len(cuttable) + 1):
        for combo in combinations(cuttable, r):
            removed_seconds = sum(s["seconds"] for s in combo)
            new_trt = current_seconds - removed_seconds
            diff = new_trt - target_seconds
            kept_segments = total_segments - r

            score = abs(diff)
            score += abs(kept_segments - desired_segments) * 30

            if prefer_under and diff > 0:
                score += 1000

            results.append({
                "score": score,
                "removed": removed_seconds,
                "new_trt": new_trt,
                "diff": diff,
                "kept": kept_segments,
                "combo": combo
            })

    results = sorted(results, key=lambda x: x["score"])

    st.subheader("Results")

    st.write(f"Current TRT: **{format_time(current_seconds)}**")
    st.write(f"Target TRT: **{format_time(target_seconds)}**")
    st.write(f"Need to Remove: **{format_time(remove_needed)}**")
    st.write(f"Total Segments: **{total_segments}**")
    st.write(f"Protected Segments: **{len(protected)}**")
    st.write(f"Cuttable Segments: **{len(cuttable)}**")

    if not results:
        st.warning("No cut combinations found. Check protection rules or segment list.")
    else:
        for i, result in enumerate(results[:5], start=1):
            st.markdown(f"## Option {i}")
            st.write(f"New TRT: **{format_time(result['new_trt'])}**")

            if result["diff"] > 0:
                st.write(f"Difference: **+{format_time(result['diff'])} over**")
            elif result["diff"] < 0:
                st.write(f"Difference: **-{format_time(abs(result['diff']))} under**")
            else:
                st.write("Difference: **EXACT MATCH**")

            st.write(f"Segments Kept: **{result['kept']}**")
            st.write(f"Time Removed: **{format_time(result['removed'])}**")

            st.write("Suggested Cuts:")
            for segment in result["combo"]:
                st.write(f"- {segment['title']} — {segment['duration']}")

            st.divider()

    with st.expander("View Protected Segments"):
        for segment in protected:
            st.write(f"- {segment['title']} — {segment['duration']}")

    with st.expander("View Cuttable Segments"):
        for segment in cuttable:
            st.write(f"- {segment['title']} — {segment['duration']}")