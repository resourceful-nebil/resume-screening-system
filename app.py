import streamlit as st
import pandas as pd

from data.dataset_loader import get_categories, get_resumes_by_category
from screening_engine import ResumeInput, ScreeningEngine

st.set_page_config(page_title="Resume Screening System", page_icon="📄", layout="wide")

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

st.title("Resume Screening System")
st.caption("Rank candidates against a job description using weighted skill matching.")

engine = ScreeningEngine()

col_jd, col_options = st.columns([2, 1])

with col_jd:
    jd_text = st.text_area(
        "Paste the job description here:",
        value=SAMPLE_JD.strip(),
        height=300,
    )

with col_options:
    source = st.radio("Resume source", ["Upload files", "Kaggle dataset"])
    use_multiprocessing = st.checkbox("Use multiprocessing", value=False)

uploaded_files = None
dataset_resumes: list[ResumeInput] = []

if source == "Upload files":
    uploaded_files = st.file_uploader(
        "Upload resume files:",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
else:
    categories = get_categories()
    default_index = categories.index("INFORMATION-TECHNOLOGY")
    selected_category = st.selectbox("Dataset category", categories, index=default_index)
    limit = st.slider("Number of resumes", min_value=5, max_value=50, value=15, step=5)
    dataset_resumes = [
        ResumeInput(name=r["name"], text=r["text"], category=r["category"])
        for r in get_resumes_by_category(selected_category, limit)
    ]
    st.info(f"Loaded **{len(dataset_resumes)}** resumes from `{selected_category}`.")

if st.button("Screen Resumes", type="primary"):
    if not jd_text.strip():
        st.error("Please paste a job description.")
        st.stop()

    resumes: list[ResumeInput] = []

    if source == "Upload files":
        if not uploaded_files:
            st.error("Please upload at least one resume file.")
            st.stop()
        for uploaded in uploaded_files:
            text = engine.resume_parser.parse(uploaded.getvalue(), uploaded.name)
            resumes.append(ResumeInput(name=uploaded.name, text=text))
    else:
        resumes = dataset_resumes

    with st.spinner(f"Screening {len(resumes)} resumes..."):
        results = engine.screen_resumes(resumes, jd_text, use_multiprocessing=use_multiprocessing)

    jd_requirements = engine.parse_jd(jd_text)

    st.success(f"Screened **{len(results)}** resumes.")

    metrics = st.columns(4)
    metrics[0].metric("Required skills", len(jd_requirements["required_skills"]))
    metrics[1].metric("Preferred skills", len(jd_requirements["preferred_skills"]))
    metrics[2].metric("Min experience", f"{jd_requirements['min_years'] or '—'} yrs")
    metrics[3].metric("Top score", f"{results[0].score}/100" if results else "—")

    table_data = []
    for rank, result in enumerate(results, start=1):
        table_data.append(
            {
                "Rank": rank,
                "Candidate": result.name,
                "Score": result.score,
                "Required Matched": ", ".join(sorted(result.required_matched)) or "—",
                "Preferred Matched": ", ".join(sorted(result.preferred_matched)) or "—",
                "Experience (yrs)": result.experience_years,
                "Category": result.category or "—",
            }
        )

    st.subheader("Ranked Results")
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    with st.expander("View detected JD requirements"):
        st.write("**Required:**", ", ".join(sorted(jd_requirements["required_skills"])) or "none detected")
        st.write("**Preferred:**", ", ".join(sorted(jd_requirements["preferred_skills"])) or "none detected")
        st.write("**Keywords:**", ", ".join(sorted(jd_requirements["keywords"])) or "none detected")
