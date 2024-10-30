import streamlit as st
import csv
from jobspy import scrape_jobs
from dotenv import load_dotenv
import pdfplumber
import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.chains import retrieval_qa
import pandas as pd
from langchain.document_loaders import CSVLoader

def analyze_resume():
        loader = TextLoader("resume.txt")
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 500,
            chunk_overlap = 0,
            length_function = len,
        )
        docs = text_splitter.split_documents(documents)
        embedding = OpenAIEmbeddings()
        library = FAISS.from_documents(docs, embedding)
        return library
        
def analyze_jobs():
    loader = CSVLoader("jobs.csv")
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=0,
        length_function=len,
    )
    docs = text_splitter.split_documents(documents)
    embedding = OpenAIEmbeddings()
    job_library = FAISS.from_documents(docs, embedding)
    return job_library

def get_recommendations(resume_library, job_library):
    query = "extract key information such as skills, experience, education, and certifications from the resume."
    resume_answer = resume_library.similarity_search(query)
    recommendations = job_library.similarity_search_by_vector(resume_answer[0])
    return recommendations

def parse_recommendations(recommendations):
    parsed_recommendations = []
    for rec in recommendations:
        job_info = {}
        lines = rec.page_content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                job_info[key.strip()] = value.strip()
        parsed_recommendations.append(job_info)
    return parsed_recommendations

def main():
    load_dotenv()
    os.getenv("OPENAI_API_KEY")
    st.title('Job Scraper 2.0')
    st.markdown("""
    <footer style="position: fixed; left: 0; bottom: 0; width: 100%; text-align: center;">
        <p style="color: grey; font-size: 0.8em;">© 2024 Vincent Wirawan. All Rights Reserved.</p>
    </footer>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader('Upload your resume *', type="pdf")
    text = ""

    if uploaded_file is None:
        st.error("Please upload a PDF file.")
        return
    else:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or "" 
                with open('resume.txt', 'w') as file:
                    file.write(text)

    position = st.text_input("Position *")
    job_loc = st.text_input("Location *")

    if st.button('Search'):
        if not position or not job_loc:
            st.warning("Please fill in all required fields marked *.")
        else:
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin"],
                search_term=position,
                location=job_loc,
                results_wanted=10,
                hours_old=72,
                country_indeed=job_loc,
                linkedin_fetch_description=True
                )
            jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)

            resume_library = analyze_resume()
            job_library = analyze_jobs()
            recommendations = get_recommendations(resume_library, job_library)
            parsed_recommendations = parse_recommendations(recommendations)

            st.subheader("Recommended Jobs")
            for job in parsed_recommendations:
                st.write(f"**Title**: {job.get('title', 'N/A')}")
                st.write(f"**Company**: {job.get('company', 'N/A')}")
                st.write(f"**Location**: {job.get('location', 'N/A')}")
                st.write(f"**Description**: {job.get('description', 'N/A')[:500]}...")  # Displaying first 500 characters of description
                st.write(f"**Job URL**: {job.get('job_url', 'N/A')}")
                st.write("---")

if __name__ == "__main__":
    main()
