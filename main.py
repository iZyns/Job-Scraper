import os
from dotenv import load_dotenv
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

load_dotenv()
api_key = os.getenv("GENAI_API_KEY")
API_KEY=api_key
MODEL=os.getenv("MODEL")

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
        #login
        service = Service(executable_path="chromedriver.exe")
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.linkedin.com/login")
        while "https://www.linkedin.com/feed" not in driver.current_url:
            pass
        driver.minimize_window()

        logging.getLogger('selenium').setLevel(logging.WARN)

        scraped_data = []
        def on_data(data: EventData):
            result = {
                'title': data.title,
                'company': data.company,
                'link': data.link,
                'skills': data.skills,
            }
            with open('jobs.txt', 'a', encoding='utf-8') as file:
                file.write(str(result) + '\n')

            scraped_data.append(result)

        def on_metrics(metrics: EventMetrics):
            print('[ON_METRICS]', str(metrics))

        def on_error(error):
            print('[ON_ERROR]', error)

        def on_end():
            print('[ON_END]')

        scraper = LinkedinScraper(
            chrome_executable_path=None,
            chrome_options=None,
            headless=True,  
            max_workers=2,
            slow_mo=0.5,
            page_load_timeout=40 
        )

        scraper.on(Events.DATA, on_data)

        query = Query(
            query=position,
            options=QueryOptions(
                limit=50,
                locations=location,
                apply_link=True,
                skip_promoted_jobs=False,
                page_offset=1,
                filters=QueryFilters(
                    experience=selected_experience_filter
                )
            )
        )
        scraper.run(query)

        resume_content = "Resume to be analyzed: " + text

        job_content = ""

        with open('jobs.txt', 'r', encoding='utf-8') as file:
            job_content = file.read()
        
        formatted_content = f"{resume_content}\n{job_content}"

        if scraped_data:
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


            client = OpenAI(api_key=API_KEY, base_url="https://api.perplexity.ai")

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=9000
            )

            #outputs result
            st.write(response.choices[0].message.content)
        else:
            st.warning("No job data scraped. Please try again!")


        driver.quit()
        # with open("jobs.txt", 'w'):
        #     pass
