import numpy as np
import duckdb as ddb

## initial data load, use in-memory DuckDb instance
con = ddb.connect()

## Create calendar table
## Dates are weekly from Week 1 / 2018 to Week 9 / 2022
with open("sql/DateTable.sql") as f:
    ddb.sql(f.read())

## Create raw input table    
ddb.read_csv('data/online-job-advert-estimates-time-series-v20.csv', encoding='UTF-8').create_view('RawData')

print(ddb.sql('SELECT * FROM Dates'))
print(ddb.sql('SELECT * FROM RawData'))
print(ddb.sql('SUMMARIZE RawData'))
