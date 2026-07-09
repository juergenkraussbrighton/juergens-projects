## Crude insights and ApEn calculations

**Crude insights and Approximate Entropy calculation for job postings**

Using the latest (2022) version of the following dataset:
- https://www.ons.gov.uk/datasets/online-job-advert-estimates/editions/time-series/versions

# Background

I was asked to provide a tool predicting a change of behaviour in clients that could lead to late payments or bad debt.
Looking at methods to analyse time series, I came across the Approximate Entropy (ApEn) statistical method.

Initially conceived to monitor physiological regular data like ECCs it is sensitive to changes in periodicy.

This tool found late applications in other areas such as finance.

The invoicing data at my workplace displayed seasonal changes, but the annual recurrence was quite strong. I had a dataset spanning 22 years.
Unfortunately I am not able to use thiis dataset here.

The available dataset from the ONS was compiled with a purpose to understand the impact of Brexit on the job market, it is an online postings index spanning January 2018 to  March 2022.

The dataset includes weekly data partitioned by Job Category, and a summary.

The Summary is a fairly smooth curve without the seasonal features, but the Education subset exhibits that to some extent.

The Output folder contains stacked plots of the normalised index year on year, where the seasonality of the Education data can be clearly seen. 

The plots for Apen and Index cover the whole timespan. The Filtering Factor has a big impact on the ApEn figures, therefore plots have been created for Education and the summary data for filtering factors 0.1, 0.15, 0.2, 0.25 and 0.5
A filtering factor of 0.15 works well for the data.

A jump in ApEn indicates an irregularity in periodic data. For perfectly periodic data the ApEn is constant.
Interpreting ApEn for data that is somewhat jagged ApEn alone is insufficient, but combined with sector knowledge and other methods it can be a valuable addition to the toolkit.

Here are a couple of events during the time covered: 
    
    '2019-07-23', 'Johnson becomes PM'
    '2019-09-09', 'Parliament prorogued'
    '2019-09-24', 'SC: prorogation unlawful'
    '2019-10-31', 'Brexit deadline 2'
    '2019-12-12', 'Con. majority (Johnson)'
    '2020-01-31', 'UK leaves EU'
    '2020-12-31', 'Transition ends'
    '2020-03-23', 'UK lockdown 1'
    '2020-11-05', 'UK lockdown 2'
    '2021-01-05', 'UK lockdown 3'

I will create another project with a dataset better suited to this kind of analysis.




