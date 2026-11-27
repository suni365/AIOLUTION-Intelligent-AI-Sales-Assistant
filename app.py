import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title='AIOLUTION | Sales Assistant', page_icon='🤖', layout='wide')
st.title('AIOLUTION | Intelligent AI Sales Assistant')
st.caption('Sales Command Center · Prototype V1')
st.info('Demo mode: no real calls are made. Use sample data only. Records are held in this browser session; export before leaving.')
statuses=['Call Pending','Prospective','Interested','Qualified','Callback Required','Meeting Requested','Proposal Required','Not Interested','Do Not Contact','Human Intervention']
fields={'Lead ID':'','Contact Name':'','Company Name':'','Phone Number':'','Contact Permission / Consent Evidence':'','Do Not Contact':'No','Lead Status':'Call Pending','Human Approval':'Pending','Call Summary':'','Follow-up Date':'','Follow-up Action':'','Last Updated':''}
if 'leads' not in st.session_state: st.session_state.leads=pd.DataFrame(columns=list(fields))
if 'history' not in st.session_state: st.session_state.history=[]
page=st.sidebar.radio('Navigation',['Dashboard','Upload Customers','Customer Management','Callbacks','Export'])
df=st.session_state.leads
if page=='Dashboard':
    cols=st.columns(4)
    for c,label,value in zip(cols,['Total leads','Interested / Qualified','Callbacks','Approved'],[len(df),df['Lead Status'].isin(['Interested','Qualified']).sum(),(df['Lead Status']=='Callback Required').sum(),(df['Human Approval']=='Approved').sum()]): c.metric(label,int(value))
    if len(df): st.bar_chart(df['Lead Status'].value_counts()); st.dataframe(df,use_container_width=True)
    else: st.write('Upload a sample Excel workbook to begin.')
elif page=='Upload Customers':
    st.subheader('Import Excel prospects')
    f=st.file_uploader('Choose an XLSX workbook',type=['xlsx'])
    if f:
        try:
            data=pd.read_excel(f,dtype=str).fillna(''); data.columns=data.columns.str.strip()
            if not {'Company Name','Phone Number'}.issubset(data.columns): st.error('Required columns: Company Name and Phone Number.')
            else:
                data=data[data['Company Name'].str.strip().ne('') & data['Phone Number'].str.strip().ne('')].copy()
                data['Phone Number']=data['Phone Number'].str.replace(r'[^0-9+]','',regex=True)
                data=data[data['Phone Number'].str.fullmatch(r'\+?[0-9]{10,15}')].drop_duplicates('Phone Number')
                for k,v in fields.items():
                    if k not in data: data[k]=v
                data['Lead ID']=['L%05d'%(i+1) for i in range(len(data))]; data['Human Approval']='Pending'; data['Lead Status']='Call Pending'
                st.dataframe(data,use_container_width=True)
                if st.button('Confirm import (replace current session leads)',disabled=data.empty):
                    st.session_state.leads=data.reset_index(drop=True); st.session_state.history=[]; st.success('Imported %d leads'%len(data))
        except Exception as e: st.error(str(e))
elif page=='Customer Management':
    if df.empty: st.warning('Upload customers first.')
    else:
        idx=st.selectbox('Select lead',list(df.index),format_func=lambda i:f"{df.at[i,'Lead ID']} — {df.at[i,'Company Name']}")
        r=df.loc[idx]; st.write('Phone:',r['Phone Number'])
        with st.form('edit'):
            status=st.selectbox('Lead status',statuses,index=statuses.index(r['Lead Status']) if r['Lead Status'] in statuses else 0)
            consent=st.text_input('Contact permission evidence',str(r['Contact Permission / Consent Evidence']))
            dnc=st.checkbox('Do not contact',value=str(r['Do Not Contact']).lower() not in ('no','false','0',''))
            approval=st.selectbox('Human approval',['Pending','Approved','Rejected'],index=['Pending','Approved','Rejected'].index(r['Human Approval']))
            summary=st.text_area('Conversation notes',str(r['Call Summary']))
            follow=st.text_input('Callback date and time (IST, YYYY-MM-DD HH:MM)',str(r['Follow-up Date']))
            action=st.text_input('Follow-up action',str(r['Follow-up Action']))
            if st.form_submit_button('Save lead'):
                try:
                    if follow: datetime.strptime(follow,'%Y-%m-%d %H:%M')
                    if status=='Callback Required' and not follow: raise ValueError('Enter a callback date and time.')
                    if dnc or status=='Do Not Contact': dnc=True; status='Do Not Contact'; approval='Rejected'; follow=''
                    if approval=='Approved' and not consent.strip(): raise ValueError('Contact permission evidence is required before approval.')
                    updates={'Lead Status':status,'Contact Permission / Consent Evidence':consent,'Do Not Contact':'Yes' if dnc else 'No','Human Approval':approval,'Call Summary':summary,'Follow-up Date':follow,'Follow-up Action':action,'Last Updated':pd.Timestamp.now(tz='Asia/Kolkata').isoformat()}
                    for k,v in updates.items(): df.at[idx,k]=v
                    st.session_state.history.append({'Lead ID':r['Lead ID'],**updates}); st.success('Lead updated.')
                except ValueError as e: st.error(str(e))
elif page=='Callbacks':
    st.subheader('Callback schedule (IST)')
    st.caption('Manual review only; automatic calling is not connected.')
    st.dataframe(df[(df['Follow-up Date']!='') & (df['Lead Status']!='Do Not Contact')].sort_values('Follow-up Date'),use_container_width=True)
else:
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl',engine_kwargs={'options':{}} if False else {}) as w:
        df.to_excel(w,index=False,sheet_name='Leads'); pd.DataFrame(st.session_state.history).to_excel(w,index=False,sheet_name='Activity')
        for sheet in w.book.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.data_type=='f': cell.data_type='s'
    st.download_button('Download updated Excel',out.getvalue(),'aiolution_leads.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
