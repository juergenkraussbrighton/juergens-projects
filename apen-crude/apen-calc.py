import re

import numpy as np
import duckdb as ddb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import datetime, date, timedelta


# Set up parameters for calculations
# reference_start and reference_end are derived automatically from the dataset inside main()
period_start = '2018-01-01'     # display window only — does not affect ApEn calculation
period_end = '2022-08-30'
run_length = 3  # typically 2 or 3
filtering_level = 0.2 # between 0.1 and 0.25 times the standard deviation of the data
window_days = 365  # look-back window in calendar days (actual data points ≈ window_days // 7 for weekly data)

export_graphs = false  # export graphs to ../Output/ folder

job_category_id = 8 
job_category = 'Education' 

# job_category_id = 30 ## '30,All industries'  # default job category for analysis
# job_category = 'All industries'  # default job category for analysis

###############################################

def main():

    ## initial data load, use in-memory DuckDb instance
    con = ddb.connect()

    ## Create raw input table    
    ddb.read_csv('data/online-job-advert-estimates-time-series-v20.csv', encoding='UTF-8').to_table('RawData')

    ## Create calendar table
    ## Dates are weekly from Week 1 / 2018 to Week 9 / 2022
    with open("sql/CreatePointsTable.sql") as f:
        ddb.execute(f.read())

    with open("sql/CreateJobCategoriesTable.sql") as f:
        ddb.execute(f.read())

    with open("sql/CreateJobIndicesTable.sql") as f:
        ddb.execute(f.read())

    ##print(ddb.sql('SELECT * FROM Points'))
    ## print(ddb.sql('SELECT * FROM RawData'))
    ## print(ddb.sql('SELECT * FROM JobIndices'))

    rel_bounds = ddb.sql('SELECT MIN(Point) AS StartDate, MAX(Point) AS EndDate FROM Points')

    rel_bounds = rel_bounds.fetchall()[0]

    print(f"Reference range: {str(rel_bounds[0])} to {str(rel_bounds[1])}")

    ## Return normalised index values for ApEn calculation, rather than absolute values
    avg_index = ddb.sql(f"""
                SELECT AVG(j.JobsIndex) as Index
                FROM Points p
                    LEFT OUTER JOIN JobIndices j 
                        ON p.YearNo = j.YearNo 
                        AND p.WeekNo = j.WeekNo
                WHERE j.JobCategoryId = {job_category_id}
                    AND p.Point 
                        BETWEEN '{str(rel_bounds[0])}' 
                        AND '{str(rel_bounds[1])}'
                """).fetchall()[0][0]

    raw_data = ddb.sql(f"""
            SELECT p.Point
                       ,WEEK(p.Point) as WeekNo
                       ,YEAR(p.Point) as YearNo
                       ,SUM(j.JobsIndex)/{avg_index} as Index
            FROM Points p
                LEFT OUTER JOIN JobIndices j 
                    ON p.YearNo = j.YearNo 
                    AND p.WeekNo = j.WeekNo
            WHERE j.JobCategoryId = {job_category_id}
                AND p.Point 
                    BETWEEN '{str(rel_bounds[0])}' 
                    AND '{str(rel_bounds[1])}'
            GROUP BY p.Point, j.JobCategoryId
            """)

    ## return absolute index values for ApEn calculation, rather than normalised values
    # raw_data = ddb.sql(f"""
    #         SELECT p.Point
    #                    ,WEEK(p.Point) as WeekNo
    #                    ,YEAR(p.Point) as YearNo
    #                    ,SUM(j.JobsIndex) as Index
    #         FROM Points p
    #             LEFT OUTER JOIN JobIndices j 
    #                 ON p.YearNo = j.YearNo 
    #                 AND p.WeekNo = j.WeekNo
    #         WHERE j.JobCategoryId = {job_category_id}
    #             AND p.Point 
    #                 BETWEEN '{str(rel_bounds[0])}' 
    #                 AND '{str(rel_bounds[1])}'
    #         GROUP BY p.Point, j.JobCategoryId
    #         """)

    stddev_index = raw_data.std('Index').fetchall()[0][0]
    r = filtering_level * stddev_index

    """ Calculate ApEn for datepoints in range, using window_days as the look-back calendar window.
        For weekly data this yields ~window_days//7 actual data points per ApEn calculation.
        The run-up interval is important to get a meaningful indication and needs to be tweaked.
        How do e.g. seasonal patterns impact the calculation?
    """
    apen_data = []
    min_points_failures = []  # dates where min_points guard triggered, TODO: error handling / logging

    approx_points_in_window = window_days // 7  # approximate actual data points (weekly data)
    min_points = max(run_length + 2, approx_points_in_window // 4)  # Option A: require at least 25% of full window

    ##df = pd.DataFrame(columns=["Point", "WeekNo", "YearNo", "Index", "ApEn"])
    
    #Loop over all data points in the full reference range; display filtering happens at plot time
    for point in raw_data.order("Point").fetchall():
        datepoint = point[0]
        data = raw_data.filter(f"Point between date_add(DATE '{datepoint}', INTERVAL '-{window_days}' DAYS) AND '{datepoint}\'").order('Point').fetchall()
        vals = [x[3] for x in data]  # Extract Indices from tuples
        if len(vals) < min_points:  # Option A: insufficient window — emit NaN rather than a misleading value
            apen_data.append({
                "Point": point[0],
                "WeekNo": point[1],
                "YearNo": point[2],
                "Index": point[3],
                "ApEn": float('nan')
            })
            min_points_failures.append(datepoint)
        else:
            apen = CalculateApEn(vals, run_length, r)
            apen_data.append({
                "Point": point[0],
                "WeekNo": point[1],
                "YearNo": point[2],
                "Index": point[3],
                "ApEn": apen
            })

    ## print(f"DatePoint, {results}")

    df = pd.DataFrame(apen_data)

    ## Plot stacked line graph year on year

    idx_grid = sns.relplot(data=df, x='WeekNo', y='Index',
                row='YearNo', kind='line',
                height=2, aspect=5,
                facet_kws={'sharex': True, 'sharey': False})

    idx_grid.set_titles(row_template='{row_name}')

    idx_grid.figure.suptitle(f'{job_category}: Job Index (weekly)', fontsize=16)
    idx_grid.figure.subplots_adjust(top=0.93)   
    
    if not export_graphs:
        plt.show()
    else:
        now_str = datetime.now().strftime('%Y%m%dT%H%M%S')  # e.g. 20250924T153045
        plt.savefig(f"./Output/{re.sub(r'[\W_]', '', job_category)}_index_plot_{now_str}.png", dpi=300)
        plt.close()


    ## Plot ApEn over time
    apen_df = df.melt(id_vars=['YearNo', 'WeekNo', 'Point'],
                value_vars=['Index', 'ApEn'],
                var_name='metric', value_name='value')


    fig, ax = plt.subplots(figsize=(14, 5))

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    sns.lineplot(data=apen_df, x='Point', y='value', hue='metric', ax=ax)
    ax.tick_params(axis='x', which='minor', length=3)
    ax.tick_params(axis='x', which='major', length=7)
    ax.grid(which='minor', axis='x', alpha=0.2)

    fig.suptitle(f'{job_category} - Job Index and ApEn (weekly), Filtering Level: {filtering_level}', fontsize=14)
    
    if not export_graphs:
        plt.show()
    else:
        now_str = datetime.now().strftime('%Y%m%dT%H%M%S')  # e.g. 20250924T153045
        plt.savefig(f"./Output/{re.sub(r'[\W_]', '', job_category)}_ApEn_plot_FL{filtering_level}_{now_str}.png", dpi=300)
        plt.close()

    print("done")

###############################################
# Approximate Entropy Calculation
###############################################
def CalculateApEn(data, m, r):
    """Calculate Approximate Entropy (ApEn) of a time series.

    Parameters:
    data : array-like
        1D array or list of numerical values representing the time series.
    m : int
        Length of compared run of data (embedding dimension).
    r : float
        Tolerance for accepting matches (typically 0.1 to 0.25 times the standard deviation of the data).

    Returns:
    float
        The approximate entropy of the time series.
    """
    def _phi(m):
        """Helper function to compute the phi value for a given m."""
        N = len(data)
        x = np.array([data[i:i + m] for i in range(N - m + 1)])
        C = np.zeros(len(x))

        for i in range(len(x)):
            C[i] = np.sum(np.max(np.abs(x - x[i]), axis=1) <= r) - 1  # exclude self-match

        return np.sum(C) / (N - m + 1)

    phi_m, phi_m1 = _phi(m), _phi(m + 1)
    return np.log(phi_m / phi_m1) if phi_m1 != 0 else float('inf')


###############################################
if __name__ == "__main__":
    main()
