import streamlit as st
st.set_page_config(layout="wide")
import os
import time
import requests
import pandas as pd

from utils.mongo import *

def reset_on_click(test=False):
    payload = {
            'test': True if test else False
        }
    requests.get("http://backend:5000/request/delete", verify=False, data=payload)

st.header("진행 현황")        

backend_status_placeholder = st.empty()
crawling_status_placeholder = st.empty()
while 1:
    if "reset" in list(st.session_state.keys()):
        st.experimental_rerun()
    # st.write(dir(st.session_state))
    with backend_status_placeholder.container():
        try:
            requests.get("http://backend:5000")
            st.info("서버 상태: 정상")
        except:
            st.warning("서버 상태: 불량")

    with crawling_status_placeholder.container():
        
        tmp = list(search_doc(MONGO_DATA_COLL, {}))
        for i in tmp:
            del i["_id"]

        if len(tmp):
            df = pd.DataFrame(tmp)[["date", "key_class", "keyword", "crawled"]].sort_values(by="date", ascending=False)
            cols = st.columns([1, 1, 1, 1])
            with cols[0]:
                subcols = st.columns([2, 1])
                with subcols[0]:
                    st.subheader("작업 대기열")
                with subcols[1]:
                    reset = st.button("초기화", key="reset", on_click=reset_on_click, args=(False,))
                st.dataframe(df[df["crawled"]=="Ready"][["date", "key_class", "keyword"]].reset_index(drop=True))
            with cols[1]:
                st.subheader("처리중")
                st.dataframe(df[df["crawled"]=="Proceeding"][["date", "key_class", "keyword"]].reset_index(drop=True))
            with cols[2]:
                st.subheader("완료")
                st.dataframe(df[df["crawled"]=="Success"][["date", "key_class", "keyword"]].reset_index(drop=True))
            with cols[3]:
                st.subheader("실패")
                st.dataframe(df[df["crawled"]=="Fail"][["date", "key_class", "keyword"]].reset_index(drop=True))
    time.sleep(60)