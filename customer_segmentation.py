# -*- coding: utf-8 -*-
"""customer_segmentation.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1j_f5yZpea8xVcCAIlIXUiFVjswkMYnpt
"""

!pip install -U dataprep

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import pandas as pd
import math
from datetime import timedelta, datetime
from dataprep.clean import clean_country
import matplotlib.pyplot as plt
# %matplotlib inline
plt.style.use("seaborn-v0_8")
plt.rcParams["figure.figsize"] = (20, 5)

"""### Exploring and preparing the data"""

from google.colab import files
uploaded = files.upload()

df1 = pd.read_csv('sales_asia.csv',
                  dtype={'week.year': str},
                  sep=';',
                  decimal=',')

# We know from domain knowledge that every row is a different sales order

df1.head()

df1.tail()

df1.shape

df1.info()

# Splitting 'week.year' column on '.' and creating 'week' and 'year' columns

df1['week'] = df1['week.year'].astype(str).str.split('.').str[0]
df1['year'] = df1['week.year'].astype(str).str.split('.').str[1]

df1.head()

# Converting year and week into date, using Monday as first day of the week

df1['date'] = pd.to_datetime(df1['year'].map(str) + df1['week'].map(str) + '-1', format='%Y%W-%w')

df1.head()

df1.columns

# Removing unnecesary columns

df2 = df1.drop(['week.year', 'week', 'year'], axis=1)

df2.head()

#Rename columns

df2.rename({'revenue': 'monetary'}, axis="columns", inplace=True)

df2.head()

df2.info()

df2.describe()

# We have 235574 transactions in the period of time icluded in the dataset
# Biggest transaction was 150,000 units. But it seems there was a return of that amount as well, -150,000 units
# Most expensive purchase was 2.41 Millions

df2.isnull().sum()

# Let's view the period of time included in the dataset

df2['date'].min()

df2['date'].max()

# Let's explore in how many different countries we have sales in that period

df2['country'].unique()

df2['country'].nunique()

# Transforming country codes into full country names with clean_country function from dataprep library

clean_country(df2, "country")['country_clean'].unique()

# Total number of customers in all countries

df2['id'].nunique()

# Putting date into the index for plotting the time series

df2b = df2.set_index("date")
df2b.head()

plt.style.use('ggplot')
plt.title('Units sold per week')
plt.ylabel('units')
plt.xlabel('date');
df2b['units'].plot(figsize=(20,5), c='dodgerblue');

plt.style.use('ggplot')
plt.title('Revenue per week')
plt.ylabel('units')
plt.xlabel('date');
df2b['monetary'].plot(figsize=(20,5), c='dodgerblue');

# For greater visibility in the plots we convert the dates to monthly periods and we aggregate the units and revenue of the same period

df2c = df2b.to_period("M")

df2c.head()

plt.style.use('ggplot')
df2c['units'].groupby('date').agg(sum).plot(figsize=(20,5), c='dodgerblue')
plt.title('Units sold per month')
plt.ylabel('units')
plt.xlabel('date');

plt.style.use('ggplot')
df2c['monetary'].groupby('date').agg(sum).plot(figsize=(20,5), c='dodgerblue')
plt.title('Revenue per month')
plt.ylabel('revenue')
plt.xlabel('date');

"""### Transform data to obtain RFM"""

print('Sales from {} to {}'.format(df2['date'].min(),
                                    df2['date'].max()))

#Let's focus on sales from last 365 days since most recent date

period = 365
date_N_days_ago = df2['date'].max() - timedelta(days=period)

# We remove the rows with dates older than 365 days ago

df2 = df2[df2['date']> date_N_days_ago]

df2.reset_index(drop=True, inplace=True)

df2.head()

df2.info()

# There are customers with the same 'id' in several countries. This causes errors in the monetary values
# Let's create a unique 'id+' identifier that combines country code and customer id

df3 = df2.copy()

df3['id+'] = df3['country'].map(str) + df3['id'].map(str)

df3.head()

# We set the NOW date one day after the last sale

NOW = df3['date'].max() + timedelta(days=1)
NOW

# We add a column, 'days_since_last_purchase', with the days between purchase date and the latest date

df3['days_since_purchase'] = df3['date'].apply(lambda x:(NOW - x).days)

df3.head()

df3[df3['id+']=='KR706854']

# Recency will be the minimum of 'days_since_last_purchase' for each customer
# Frequency will be the total number of orders in the period for each customer

aggr = {
    'days_since_purchase': lambda x:x.min(),
    'date': lambda x: len([d for d in x if d >= NOW - timedelta(days=period)])
}

aggr

rfm = df3.groupby(['id', 'id+', 'country']).agg(aggr).reset_index()
rfm.rename(columns={'days_since_purchase': 'recency',
                   'date': 'frequency'},
          inplace=True)

rfm

# We check customers with id 3790218 have different recency and frequency values per country

rfm[rfm['id']==3790218]

# We get the revenue of the last 365 days per customer

df3[df3['date'] >= NOW - timedelta(days=period)]\
    .groupby('id+')['monetary'].sum()

# Example: getting only the monetary value for specific customer with id 3790218

df3[ (df3['id'] == 3790218) & (df3['date'] >= NOW - timedelta(days=period))]\
    .groupby('id+')['monetary'].sum()

from datetime import timedelta

rfm['monetary'] = rfm['id+'].apply(
    lambda x: df3[
        (df3['id+'] == x) & (df3['date'] >= NOW - timedelta(days=period))
    ]
    .groupby(['id', 'country'])
    .sum(numeric_only=True)
    .iloc[0, 0]
)

rfm.head()

# Checking monetary value is correct by checking on our biggest customer

rfm[rfm['monetary']==rfm['monetary'].max()]

rfm[rfm['frequency']==rfm['frequency'].max()]

# We check that customers with id 3790218 get a different monetary value per country

rfm[rfm['id']==3790218]

# Let's frop the column 'id+'

rfm.drop(['id+'], axis=1, inplace=True)

"""### Calculate the R, F and M scores"""

# We assign a rate between 1 and 5 depending on recency, monetary and frequency parameters
# We use the quintiles method, dividing every feature on groups that contain 20 % of the samples

quintiles = rfm[['recency', 'frequency', 'monetary']].quantile([.2, .4, .6, .8]).to_dict()
quintiles

# Assigning scores from 1 to 5
# Higher values are better for frequency and monetary, while lower values are better for recency

def r_score(x):
    if x <= quintiles['recency'][.2]:
        return 5
    elif x <= quintiles['recency'][.4]:
        return 4
    elif x <= quintiles['recency'][.6]:
        return 3
    elif x <= quintiles['recency'][.8]:
        return 2
    else:
        return 1

def fm_score(x, c):
    if x <= quintiles[c][.2]:
        return 1
    elif x <= quintiles[c][.4]:
        return 2
    elif x <= quintiles[c][.6]:
        return 3
    elif x <= quintiles[c][.8]:
        return 4
    else:
        return 5

# We asssign R, F and M scores to each customer

rfm['r'] = rfm['recency'].apply(lambda x: r_score(x))
rfm['f'] = rfm['frequency'].apply(lambda x: fm_score(x, 'frequency'))
rfm['m'] = rfm['monetary'].apply(lambda x: fm_score(x, 'monetary'))

rfm.head()

# Combine R, F and M scores to create a unique RFM score

rfm['rfm_score'] = rfm['r'].map(str) + rfm['f'].map(str) + rfm['m'].map(str)
rfm.head()

# With this rfm scores we would have 125 segments of customers
# To make a more simple segment map of 11 segments, we combine f and m scores, rounding them down
# fm = (f+m)/2

def truncate(x):
    return math.trunc(x)

rfm['fm'] = ((rfm['f'] + rfm['m'])/2).apply(lambda x: truncate(x))

rfm.head()

"""### Segment	Description
* **Champions**	Bought recently, buy often and spend the most
* **Loyal Customers**	Buy on a regular basis. Responsive to promotions.
* **Potential Loyalists**	Recent customers with average frequency.
* **Recent Customers**	Bought most recently, but not often.
* **Promising**	Recent shoppers, but haven’t spent much.
* **Customers Needing Attention**	Above average recency, frequency and monetary values. May not have bought very recently though.
* **About To Sleep**	Below average recency and frequency. Will lose them if not reactivated.
* **At Risk**	Purchased often but a long time ago. Need to bring them back!
* **Can’t Lose Them**	Used to purchase frequently but haven’t returned for a long time.
* **Hibernating**	Last purchase was long back and low number of orders.
* **Lost** Purchased long time ago and never came back.
"""

# We create a segment map of only 11 segments based on only two scores: 'r' and 'fm'

segment_map = {
    r'22': 'hibernating',
    r'[1-2][1-2]': 'lost',
    r'15': 'can\'t lose',
    r'[1-2][3-5]': 'at risk',
    r'3[1-2]': 'about to sleep',
    r'33': 'need attention',
    r'55': 'champions',
    r'[3-5][4-5]': 'loyal customers',
    r'41': 'promising',
    r'51': 'new customers',
    r'[4-5][2-3]': 'potential loyalists'
}

rfm['segment'] = rfm['r'].map(str) + rfm['fm'].map(str)
rfm['segment'] = rfm['segment'].replace(segment_map, regex=True)
rfm.head()

rfm.isnull().sum()

"""### Exploring the customers segments"""

rfm['segment'].unique()

# We take a look on some segments

rfm[rfm['segment']=="can't lose"].sort_values(by='monetary', ascending=False)

rfm[rfm['segment']=="need attention"].sort_values(by='monetary', ascending=False).head(10)

rfm[rfm['segment']=='loyal customers'].sort_values(by='monetary', ascending=False).head(10)

rfm[rfm['segment']=='champions'].sort_values(by='monetary', ascending=False).head(10)

rfm['monetary'].mean()

# Customers with monetary over the average that need attention

rfm[(rfm['monetary']>rfm['monetary'].mean()) & (rfm['segment']=='need attention')]\
    .sort_values(by='monetary', ascending=False)

# Using 'monetary' as the size of the points, we see that the majority of customers who spend the most also purchase more frequently

plt.style.use('ggplot')
rfm.plot.scatter(x='recency', y='frequency', s=rfm['monetary']*5e-5, figsize=(20,5), c='dodgerblue')
plt.gca().set(xlabel='recency', ylabel='frequency', title='Customer distribution');

# We export the dataframe to a CSV file for later processing it in Power BI

rfm.to_csv('rfm_asia.csv', encoding='utf-8', index=False, float_format='%.2f')

from google.colab import files
files.download('rfm_asia.csv')