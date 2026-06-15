import io
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

from data.dataset_loader import get_categories, get_resumes_by_category
from screening_engine import ResumeInput, ScreeningEngine
from utils.export import results_to_dataframe

st.set_page_config(
    page_title="Resume Screening System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 600; color: #2c3e50; text-align: center; margin-bottom: 0.25rem; }
    .sub-header { font-size: 1rem; color: #7f8c8d; text-align: center; margin-bottom: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

SAMPLE_JD = """We are looking for a Senior Python Developer with strong experience in backend development.

Required Skills:
- Python
- Django
- REST APIs
- SQL

Preferred Skills:
- PostgreSQL
- Docker
- AWS

Experience:
- 3+ years of professional Python development
- Experience building web applications
"""


ENGINE_CACHE_VERSION = 2


@st.cache_resource
def load_engine(_cache_version: int = ENGINE_CACHE_VERSION):
    return ScreeningEngine()


engine = load_engine(ENGINE_CACHE_VERSION)

st.markdown('<div class="main-header">Resume Screening System</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Rank candidates using weighted skill, experience, and keyword matching</div>',
    unsafe_allow_html=True,
)

st.sidebar.header("Configuration")
top_n = st.sidebar.number_input("Top N matches", min_value=1, max_value=100, value=10)
min_score = st.sidebar.number_input("Minimum score (%)", min_value=0.0, max_value=100.0, value=0.0)
if min_score == 0.0:
    min_score_filter = None
else:
    min_score_filter = min_score

use_multiprocessing = st.sidebar.checkbox("Use multiprocessing", value=False)
st.sidebar.markdown("---")
st.sidebar.markdown("### Scoring Weights")
st.sidebar.markdown("**Required Skills**: 50%")
st.sidebar.markdown("**Preferred Skills**: 25%")
st.sidebar.markdown("**Experience**: 15%")
st.sidebar.markdown("**Keywords**: 10%")

col_jd, col_resumes = st.columns([1, 1])

jd_data = None
jd_text = ""

with col_jd:
    st.subheader("Job Description")
    jd_input_method = st.radio("JD input", ["Paste text", "Upload file"], horizontal=True)

    if jd_input_method == "Paste text":
        jd_text = st.text_area("Paste job description:", value=SAMPLE_JD.strip(), height=320)
        if jd_text.strip():
            try:
                jd_data = engine.parse_jd(jd_text)
                with st.expander("JD parsed successfully", expanded=False):
                    st.write(f"**Required skills:** {len(jd_data['required_skills'])}")
                    if jd_data["required_skills"]:
                        st.write(f"Sample: {', '.join(sorted(jd_data['required_skills'])[:6])}")
                    st.write(f"**Preferred skills:** {len(jd_data['preferred_skills'])}")
                    st.write(f"**Min experience:** {jd_data['min_years']} years")
            except Exception as exc:
                st.error(f"Error parsing job description: {exc}")
    else:
        jd_file = st.file_uploader("Upload JD file", type=["txt", "pdf", "docx", "doc"])
        if jd_file:
            import tempfile
            from pathlib import Path

            suffix = Path(jd_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(jd_file.getvalue())
                tmp_path = tmp.name
            try:
                jd_data = engine.parse_jd_file(tmp_path)
                jd_text = jd_data["text"]
                with st.expander("JD parsed successfully", expanded=False):
                    st.write(f"**Required skills:** {len(jd_data['required_skills'])}")
                    st.write(f"**Preferred skills:** {len(jd_data['preferred_skills'])}")
                    st.write(f"**Min experience:** {jd_data['min_years']} years")
            except Exception as exc:
                st.error(f"Error parsing job description: {exc}")
            finally:
                Path(tmp_path).unlink(missing_ok=True)

with col_resumes:
    st.subheader("Resumes")
    source = st.radio("Resume source", ["Upload files", "Kaggle dataset"], horizontal=True)

    uploaded_files = None
    dataset_resumes: list[ResumeInput] = []

    if source == "Upload files":
        uploaded_files = st.file_uploader(
            "Upload resume files",
            type=["txt", "pdf", "docx", "doc"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            st.success(f"{len(uploaded_files)} resume files uploaded")
            with st.expander("View uploaded files", expanded=False):
                for idx, file in enumerate(uploaded_files[:20], start=1):
                    st.text(f"{idx}. {file.name}")
                if len(uploaded_files) > 20:
                    st.text(f"... and {len(uploaded_files) - 20} more")
    else:
        categories = get_categories()
        default_index = categories.index("INFORMATION-TECHNOLOGY")
        selected_category = st.selectbox("Dataset category", categories, index=default_index)
        limit = st.slider("Number of resumes", min_value=5, max_value=50, value=15, step=5)
        dataset_resumes = [
            ResumeInput(name=r["name"], text=r["text"], category=r["category"], filename=r["name"])
            for r in get_resumes_by_category(selected_category, limit)
        ]
        st.info(f"Loaded **{len(dataset_resumes)}** resumes from `{selected_category}`.")

st.markdown("---")
_, col_btn, _ = st.columns([1, 1, 1])
with col_btn:
    process_button = st.button("Start Screening", type="primary", use_container_width=True)

if process_button:
    if not jd_data and not jd_text.strip():
        st.error("Please provide a job description.")
        st.stop()

    resumes: list[ResumeInput] = []

    if source == "Upload files":
        if not uploaded_files:
            st.error("Please upload at least one resume file.")
            st.stop()
        progress = st.progress(0)
        for idx, uploaded in enumerate(uploaded_files):
            parsed = engine.resume_parser.parse_upload(uploaded.getvalue(), uploaded.name)
            resumes.append(
                ResumeInput(
                    name=uploaded.name,
                    text=parsed["text"],
                    email=parsed["email"],
                    phone=parsed["phone"],
                    candidate_name=parsed["name"],
                    filename=parsed["file_name"],
                    file_bytes=parsed.get("file_bytes"),
                )
            )
            progress.progress((idx + 1) / len(uploaded_files))
    else:
        resumes = dataset_resumes

    start_time = datetime.now()
    with st.spinner(f"Screening {len(resumes)} resumes..."):
        results = engine.screen_resumes(
            resumes,
            jd_text=jd_text if jd_data is None else None,
            jd_requirements=jd_data,
            use_multiprocessing=use_multiprocessing,
            top_n=top_n,
            min_score=min_score_filter,
        )

    if not results:
        st.warning("No resumes matched the minimum score threshold.")
        st.stop()

    elapsed = (datetime.now() - start_time).total_seconds()
    st.success(f"Screening completed in {elapsed:.2f} seconds — **{len(results)}** candidates returned.")

    avg_score = sum(r.score for r in results) / len(results)
    metrics = st.columns(4)
    metrics[0].metric("Processed", len(resumes))
    metrics[1].metric("Returned", len(results))
    metrics[2].metric("Average score", f"{avg_score:.1f}%")
    metrics[3].metric("Top score", f"{results[0].score:.1f}%")

    df = results_to_dataframe(results)
    st.subheader("Ranked Results")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if jd_data is None and jd_text.strip():
        jd_data = engine.parse_jd(jd_text)

    with st.expander("Detected JD requirements"):
        st.write("**Required:**", ", ".join(sorted(jd_data["required_skills"])) or "none")
        st.write("**Preferred:**", ", ".join(sorted(jd_data["preferred_skills"])) or "none")
        st.write("**Keywords:**", ", ".join(sorted(set(jd_data["keywords"]))) or "none")

    st.markdown("### Export Options")
    col_csv, col_json, col_zip = st.columns(3)

    with col_csv:
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_json:
        st.download_button(
            label="Download JSON",
            data=df.to_json(orient="records", indent=2),
            file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_zip:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, result in enumerate(results, start=1):
                if result.file_bytes:
                    ranked_name = f"{idx:02d}_{result.filename}"
                    zip_file.writestr(ranked_name, result.file_bytes)
        if any(r.file_bytes for r in results):
            st.download_button(
                label="Download Resumes (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"top_resumes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.caption("ZIP export available for uploaded files only.")

    st.markdown("### Detailed Profiles")
    for idx, result in enumerate(results[:10], start=1):
        display_name = result.candidate_name or result.name
        with st.expander(f"Rank #{idx} — {display_name} — {result.score:.1f}%"):
            detail_left, detail_right = st.columns(2)

            with detail_left:
                st.markdown("**Candidate Information**")
                st.write(f"Resume: {result.filename or result.name}")
                st.write(f"Name: {display_name}")
                st.write(f"Email: {result.email or 'N/A'}")
                st.write(f"Phone: {result.phone or 'N/A'}")
                st.write(f"Experience: {result.experience_years} years")
                if result.category:
                    st.write(f"Category: {result.category}")

            with detail_right:
                st.markdown("**Score Breakdown**")
                st.write(f"Required skills: {result.required_score:.1f}%")
                st.write(f"Preferred skills: {result.preferred_score:.1f}%")
                st.write(f"Experience: {result.experience_score:.1f}%")
                st.write(f"Keywords: {result.keyword_score:.1f}%")

            st.markdown("**Matched Skills**")
            matched = sorted(result.required_matched | result.preferred_matched)
            st.write(", ".join(matched) if matched else "No matching skills found")

            st.markdown("**Missing Required Skills**")
            st.write(", ".join(sorted(result.missing_required)) if result.missing_required else "None")

            if result.file_bytes:
                st.download_button(
                    label="Download resume",
                    data=result.file_bytes,
                    file_name=result.filename,
                    mime="application/octet-stream",
                    key=f"download_resume_{idx}",
                )
