import streamlit as st
from itertools import combinations

# -----------------------------
# TRT Helper Functions
# -----------------------------

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


# -----------------------------
# Page Setup
# -----------------------------

st.set_page_config(page_title="TRT Cut Assistant", layout="wide")

st.title("TRT Cut Assistant")

st.write("Upload a timing screenshot for reference, then paste segments below.")

# -----------------------------
# Screenshot Upload
# -----------------------------

uploaded_file = st.file_uploader(
    "Upload timing screenshot",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.image(
        uploaded_file,
        caption="Uploaded Timing Screenshot",
        use_container_width=True
    )

    st.info(
        "Screenshot upload is currently for visual reference. Paste the segment timings manually below."
    )

# -----------------------------
# Inputs
# -----------------------------

current_trt = st.text_input(
    "Current TRT",
    "02:25:39:00"
)

target_trt = st.text_input(
    "Target TRT",
    "02:01:45:00"
)

desired_segments = st.number_input(
    "Desired Kept Segments",
    min_value=1,
    value=14
)

prefer_under = st.checkbox(
    "Prefer Staying Under TRT",
    value=False
)

st.write("Paste segments in this format:")
st.code("SEGMENT NAME, 00:05:32")

segment_input = st.text_area(
    "Segments",
    """OPEN STL|ATH, 00:02:16
T1ST 0|0, 00:05:42
B1ST 0|1, 00:06:49
T2ND, 00:05:44
B2ND, 00:08:08
T3RD, 00:07:13
B3RD, 00:06:20
FINAL 6|0, 00:16:34""",
    height=250
)

# -----------------------------
# Main Logic
# -----------------------------

if st.button("Find Best Cuts"):

    current_seconds = to_seconds(current_trt)
    target_seconds = to_seconds(target_trt)
    remove_needed = current_seconds - target_seconds

    segments = []

    protected_keywords = [
        "OPEN",
        "FINAL",
        "B1ST",
        "T1ST"
    ]

    # Parse Segment Data
    for line in segment_input.splitlines():

        if not line.strip():
            continue

        try:
            title, duration = [x.strip() for x in line.split(",")]

            title_upper = title.upper()

            # Automatic Protection Rules
            if any(keyword in title_upper for keyword in protected_keywords):
                rule = "keep"
            elif "|" in title_upper:
                rule = "keep"
            else:
                rule = "cuttable"

            segments.append({
                "title": title,
                "duration": duration,
                "seconds": to_seconds(duration),
                "rule": rule
            })

        except:
            st.error(f"Problem reading line: {line}")

    cuttable = [s for s in segments if s["rule"] == "cuttable"]
    protected = [s for s in segments if s["rule"] == "keep"]

    total_segments = len(segments)

    results = []

    # Brute Force Combinations
    for r in range(1, len(cuttable) + 1):

        for combo in combinations(cuttable, r):

            removed_seconds = sum(s["seconds"] for s in combo)
            new_trt = current_seconds - removed_seconds
            diff = new_trt - target_seconds
            kept_segments = total_segments - r

            # Scoring formula
            score = abs(diff)

            # Segment count preference
            score += abs(kept_segments - desired_segments) * 30

            # Prefer under target if selected
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

    # -----------------------------
    # Display Results
    # -----------------------------

    st.subheader("Results")

    st.write(f"Current TRT: **{format_time(current_seconds)}**")
    st.write(f"Target TRT: **{format_time(target_seconds)}**")
    st.write(f"Need to Remove: **{format_time(remove_needed)}**")

    st.write(f"Total Segments: **{total_segments}**")
    st.write(f"Protected Segments: **{len(protected)}**")
    st.write(f"Cuttable Segments: **{len(cuttable)}**")

    if not results:
        st.warning("No cut combinations found. Check your segment list.")
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

    # -----------------------------
    # Protected Segment List
    # -----------------------------

    with st.expander("View Protected Segments"):
        for segment in protected:
            st.write(f"- {segment['title']} — {segment['duration']}")

    with st.expander("View Cuttable Segments"):
        for segment in cuttable:
            st.write(f"- {segment['title']} — {segment['duration']}")