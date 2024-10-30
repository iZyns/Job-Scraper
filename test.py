
import streamlit as st
import pdfplumber
import logging
import platform
from openai import OpenAI
from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import Events, EventData, EventMetrics
from linkedin_jobs_scraper.query import Query, QueryOptions, QueryFilters
from linkedin_jobs_scraper.filters import ExperienceLevelFilters
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import google.generativeai as genai
import os
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
perplexity_key = os.getenv("PERPLEXITY_API_KEY")
st.title('Job Scraper 1.0')
st.markdown("""
<footer style="position: fixed; left: 0; bottom: 0; width: 100%; text-align: center;">
    <p style="color: grey; font-size: 0.8em;">© 2024 Vincent Wirawan. All Rights Reserved.</p>
</footer>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader('Upload your resume *', type="pdf")
text = ""

if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
else:
    st.error("Please upload a PDF file.")

position = st.text_input("Position *")
location = st.text_input("Location *")
exp_level = st.selectbox('Experience Level',('Internship', 'Entry Level','Associate','Mid-Senior Level',"Director"))
experience_mapping = {
    'Internship': ExperienceLevelFilters.INTERNSHIP,
    'Entry Level': ExperienceLevelFilters.ENTRY_LEVEL,
    'Associate': ExperienceLevelFilters.ASSOCIATE,
    'Mid-Senior Level': ExperienceLevelFilters.MID_SENIOR,
    'Director': ExperienceLevelFilters.DIRECTOR
}
selected_experience_filter = experience_mapping.get(exp_level)
if st.button('Search'):
    if not position or not location:
        st.warning("Please fill in all required fields marked *.")
    else:
        resume_content = "Resume to be analyzed: " + text

        job_content = ""

        with open('jobs.txt', 'r', encoding='utf-8') as file:
            job_content = file.read()
        
        formatted_content = f"{resume_content}\n{job_content}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You’re an experienced resume analyst, skilled at reviewing resumes and matching job positions to candidates based on their skills and experiences. Your task is to analyze a resume provided and sort a list of job positions with skills and descriptions from most relevant to least relevant, based on the information presented in the resume."
                    "Please review the provided resume carefully, paying attention to the candidate's skills, experiences, and qualifications. Use this information to match the candidate with the most suitable job positions listed in the database. Ensure that the sorting is done in ascending order of relevance, with the most relevant job position appearing at the top of the list."
                    "Make sure to keep the format of the job postings as it is and include the complete link to the job posting. Remove any duplicate job postings."
                ),
            },
            {
                "role": "user",
                "content": (
                    formatted_content
                ),
            },
        ]


        client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")

        response = client.chat.completions.create(
            model="llama-3-sonar-large-32k-chat",
            messages=messages,
        )

        st.write(response.choices[0].message.content)
