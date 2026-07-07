import numpy as np
import duckdb as ddb


# Set up parameters for calculations
# reference_start and reference_end are derived automatically from the dataset inside main()
period_start = '2018-01-01'     # display window only — does not affect ApEn calculation
period_end = '2022-08-30'
run_length = 3  # typically 2 or 3
filtering_level = 0.5 # between 0.1 and 0.25 times the standard deviation of the data
window_days = 365  # look-back window in calendar days (actual data points ≈ window_days // 7 for weekly data)
job_category = 'All industries'  # default job category for analysis

###############################################

def main():

    ## initial data load, use in-memory DuckDb instance
    con = ddb.connect()

    ## Create raw input table    
    ddb.read_csv('data/online-job-advert-estimates-time-series-v20.csv', encoding='UTF-8').to_table('RawData')

    ## Create calendar table
    ## Dates are weekly from Week 1 / 2018 to Week 9 / 2022
    with open("sql/CreatePointsTable.sql") as f:
        ddb.sql(f.read())

    with open("sql/CreateJobCategoriesTable.sql") as f:
        ddb.sql(f.read())

    with open("sql/CreateJobIndicesTable.sql") as f:
        ddb.sql(f.read())

    ##print(ddb.sql('SELECT * FROM Points'))
    ## print(ddb.sql('SELECT * FROM RawData'))
    ## print(ddb.sql('SELECT * FROM JobIndices'))

    rel_bounds = ddb.sql('SELECT MIN(Point) AS StartDate, MAX(Point) AS EndDate FROM Points')

    rel_bounds = rel_bounds.fetchall()[0]

    print(f"Reference range: {str(rel_bounds[0])} to {str(rel_bounds[1])}")

    avg_index = ddb.sql(f"""
                SELECT AVG(j.JobsIndex) as Index
                FROM Points p
                    LEFT OUTER JOIN JobIndices j 
                        ON p.YearNo = j.YearNo 
                        AND p.WeekNo = j.WeekNo
                    LEFT OUTER JOIN JobCategories c 
                        ON j.JobCategoryId = c.id  
                WHERE c.JobCategory = '{job_category}' 
                    AND p.Point 
                        BETWEEN '{str(rel_bounds[0])}' 
                        AND '{str(rel_bounds[1])}'
                """).fetchall()[0][0]

    raw_data = ddb.sql(f"""
            SELECT p.Point, SUM(j.JobsIndex)/{avg_index} as Index
            FROM Points p
                LEFT OUTER JOIN JobIndices j 
                    ON p.YearNo = j.YearNo 
                    AND p.WeekNo = j.WeekNo
                LEFT OUTER JOIN JobCategories c 
                    ON j.JobCategoryId = c.id  
            WHERE c.JobCategory = '{job_category}' 
                AND p.Point 
                    BETWEEN '{str(rel_bounds[0])}' 
                    AND '{str(rel_bounds[1])}'
            GROUP BY p.Point, c.JobCategory
            """)

    stddev_amount = raw_data.std('Index').fetchall()[0][0]
    r = filtering_level * stddev_amount
    
    """ Calculate ApEn for datepoints in range, using window_days as the look-back calendar window.
        For weekly data this yields ~window_days//7 actual data points per ApEn calculation.
        The run-up interval is important to get a meaningful indication and needs to be tweaked.
        How do e.g. seasonal patterns impact the calculation?
    """
    results = []
    min_points_failures = []  # dates where min_points guard triggered

    approx_points_in_window = window_days // 7  # approximate actual data points (weekly data)
    min_points = max(run_length + 2, approx_points_in_window // 4)  # Option A: require at least 25% of full window

    #Loop over all data points in the full reference range; display filtering happens at plot time
    for point in raw_data.order("Point").fetchall():
        datepoint = point[0]
        data = raw_data.filter(f"Point between date_add(DATE '{datepoint}', INTERVAL '-{window_days}' DAYS) AND '{datepoint}\'").order('Point').fetchall()
        vals = [x[1] for x in data]  # Extract Indices from tuples
        if len(vals) < min_points:  # Option A: insufficient window — emit NaN rather than a misleading value
            results.append((point[0], point[1], float('nan')))
            min_points_failures.append(datepoint)
        else:
            apen = CalculateApEn(vals, run_length, r)
            results.append((point[0], point[1], apen))

    ## print(f"DatePoint, {results}")


    ## TODO: Plot stacked line graph year on year

    ## TODO: Plot ApEn over time


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
