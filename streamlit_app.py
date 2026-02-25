
import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, date

demand=pd.read_csv('train.csv', header=0)
demand['date']=pd.to_datetime(demand['date'])
demand['date']=demand['date']+timedelta(days=3650)
demand=demand[demand['item']<=10]
demand=demand[demand['store']<=5]
stores=demand['store'].unique()
items=demand['item'].unique()

st.title("Product Demand Forecast")
with st.container(border=True):
    c1,c2=st.columns(2)
    with c1:
        sel_stores = st.multiselect("Stores", stores, default=stores)
    with c2:
        sel_items = st.selectbox("Item", items)
filter=demand[(demand['store'].isin(sel_stores))&(demand['item']==(sel_items))]
filter=filter.drop(columns=['store','item'])
data=filter.groupby('date').agg('sum').reset_index()
data['cat']=np.where(data['date']<'2026-01-01', 'Historic','Forecast')
data['avg7'] = data['sales'].rolling(window=7).mean()
data['demand']=np.where(data['cat']=='Forecast',data['avg7'],data['sales'])
tab1, tab2 = st.tabs(["Demand Forecast", "Reorder Point"])

stock=data[data['date'].dt.date>date.today()].reset_index()
stock=stock[['date','demand']]
stock['demand']=stock['demand'].apply(lambda x:math.ceil(x))
with tab1:
    c1,c2,c3=st.columns(3)
    st.line_chart(data, x='date', y='demand',color='cat', height=400)

with tab2:
    c1,c2,c3=st.columns(3)
    with c1:
        safety=st.number_input("Safety Stock",min_value=0)
    with c2:
        lead=st.number_input("Lead Time (days)", min_value=1)
    with c3:
        o_freq=st.number_input("Order Frequency (days)",min_value=1)
    stock['reorder']=np.where(stock.index % o_freq == 0,True,False)
    stock['receive']=np.where(stock['reorder']==True,stock['date']+timedelta(days=lead),pd.NA)
    stock['receive']=pd.to_datetime(stock['receive'])
    #req=req.groupby('receive').agg('sum')
    reo=stock[stock['reorder']==True][['date','receive']]
    reo=reo.rename(columns={'date': 'order_by','receive':'arrive'})
    stock=pd.merge(stock,reo,left_on='date',right_on='arrive',how='left')
    stock['order_by'] = stock['order_by'].fillna(method='ffill')
    req=stock[['order_by','demand']].dropna()
    req=req.groupby('order_by').agg('sum')
    req=req.rename(columns={'demand':'batch_demand'})
    reo=reo.join(req,on='order_by',how='left')
    stock=stock.drop(columns=['receive','order_by','arrive'])
    stock=pd.merge(stock,reo[['order_by','batch_demand']],left_on='date',right_on='order_by',how='left')
    stock=pd.merge(stock,reo[['arrive','batch_demand']],left_on='date',right_on='arrive',how='left')
    ini_st=safety+stock[stock['date']<stock['arrive'].min()]['demand'].sum()
    stock=stock.drop(columns=['order_by','arrive'])
    stock=stock.rename(columns={'batch_demand_x':'Order','batch_demand_y':'Arrive'})
    stock=stock.fillna(0)
    stock['delta']=stock['Arrive']-stock['demand']
    delt=stock['delta'].tolist()
    n=[]
    for i in delt:
        ini_st+=i
        n.append(ini_st)
    stock['stock']=n
    f1=px.bar(stock,x='date',y='Order',color_discrete_sequence=['crimson'])
    f1.update_traces(marker_line_width=0,name='Order QTY')
    f2=px.line(stock,x='date',y='stock',line_shape='hv',color_discrete_sequence=['rgb(15, 139, 141)'])
    f2.update_traces(name='Stock Level')
    f3=px.line(stock,x='date',y='demand',markers=True,color_discrete_sequence=['rgb(236, 154, 41)'])
    f3.update_traces(name='Demand Forecast')
    fig=f1.add_trace(f2.data[0])
    fig=fig.add_trace(f3.data[0])
    #fig=go.Figure(data=f1.data+f2.data+f3.data)
    fig.update_xaxes(range=[date.today(),date.today()+timedelta(days=30)])
    fig.update_yaxes(title_text="Units")
    fig.update_traces(showlegend=True)
    st.write('Stock Forecast')
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)
    st.write('Item Reorder Schedule')
    st.dataframe(reo)
