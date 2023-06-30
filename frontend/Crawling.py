import streamlit as st
st.set_page_config(layout="wide")

import requests
import os
import threading
from datetime import datetime

import pandas as pd

import utils
from utils.api import request_crwling
from utils.mongo import *

cond = False

with st.form("File Transfer", clear_on_submit=False):
    uploaded_file = st.file_uploader(label="엑셀 파일 업로드", type=["xlsx", "xls"])
    submitted = st.form_submit_button("크롤링 시작!")
    
    
    if submitted:
        if not uploaded_file:
            st.error("파일을 업로드 해주세요!")
            st.stop()
        else:
            if submitted:     
                bytes_data = uploaded_file.getvalue()        
                crawling_list=pd.read_excel(bytes_data)[["class", "keyword"]]
                crawling_list = crawling_list[~crawling_list["class"].isnull()]
                crawling_thread = threading.Thread(target=request_crwling, name="Crawling", args=[bytes_data])
                crawling_thread.start()
                cond = True
            
    if cond:    
        st.info("Start Crawling")
    html_string = '수집 현황은 <a href="http://192.168.0.141:8501/check_crawling" target="_self">처리 현황</a>에서 확인하세요!'
    st.markdown(html_string, unsafe_allow_html=True)
