import numpy as np
import duckdb as ddb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from datetime import datetime, date, timedelta

# Load data into DuckDB
con = ddb.connect()
# ddb.sql("""CREATE TABLE Points AS select distinct Point from '../Data/PaymentsReceipts.csv'""")
# ddb.read_csv('../Data/Companies.csv', encoding='UTF-8').create_view('Companies')
# ddb.read_csv('../Data/PaymentsReceipts.csv', encoding='UTF-8').create_view('PaymentsReceipts')
# ddb.read_csv('../Data/PaymentsReceiptsOneZero.csv', encoding='UTF-8').create_view('PaymentsReceipts')
# ddb.read_csv('../Data/PaymentsReceiptsOneZeroRnd.csv', encoding='UTF-8').create_view('PaymentsReceipts')
# ddb.read_csv('../Data/PaymentsReceiptsSine.csv', encoding='UTF-8').create_view('PaymentsReceipts')

dataset_file = '../Data/PaymentsReceipts.csv'
ddb.sql(f"""CREATE TABLE Points AS select distinct Point from '{dataset_file}'""")
ddb.read_csv(dataset_file, encoding='UTF-8').create_view('PaymentsReceipts')
ddb.sql("""CREATE VIEW Companies AS SELECT DISTINCT CompanyId AS ID, CompanyId AS Company FROM PaymentsReceipts""")
#ddb.read_csv('../Data/online-job-advert-estimates-time-series-jk-All.csv', encoding='UTF-8').create_view('PaymentsReceipts')

# Set up parameters for calculations
# reference_start and reference_end are derived automatically from the dataset inside main()
period_start = '2014-01-01'     # display window only — does not affect ApEn calculation
period_end = '2025-12-24'
run_length = 3  # typically 2 or 3
filtering_level = 0.5 # between 0.1 and 0.25 times the standard deviation of the data
window_days = 365  # look-back window in calendar days (actual data points ≈ window_days // 7 for weekly data)
transaction_type = 'SI'  # 'SI' for Invoices, 'SR' for Receipts, 'JA' for Job Adverts

# Company ID as Parameter
company_id = 'ALL'

# smoothing window (in number of points) for Amount
smoothing_window = 10  # set to 1 to disable smoothing
show_events   = True  # set to True to show key event markers
show_holidays = True  # set to True to show holiday shading and bank holiday lines
show_amount   = False  # set to False to hide the raw value line
show_smoothed = False  # set to False to hide the MA smoothed line

# Brexit and COVID key events — (date, label, color)
KEY_EVENTS = [
    ('2014-05-22', 'EU Parliament\nelections',   '#9b59b6'),
    ('2015-05-07', 'Con. majority\n(Cameron)',   '#2e8b57'),
    ('2016-06-23', 'Brexit\nreferendum',  '#1a6bbd'),
    ('2016-10-02', 'Art.50 by\nMar 2017', '#1a6bbd'),
    ('2016-10-06', 'Fracking\napproved',  '#b8860b'),
    ('2017-03-29', 'Art.50\ntriggered',   '#1a6bbd'),
    ('2017-06-08', 'Snap\nelection',      '#2e8b57'),
    ('2017-06-14', 'Grenfell\nTower',     '#b22222'),
    ('2017-06-26', 'DUP\ndeal',           '#2e8b57'),
    ('2017-10-29', 'Sex. harass.\nscandal', '#8b008b'),
    ('2017-11-14', 'Inflation\npeak 3.1%','#cc6600'),
    ('2017-12-13', 'Tory\nrebellion',     '#2e8b57'),
    ('2018-11-09', 'Jo Johnson\nresigns',  '#2e8b57'),
    ('2018-11-14', 'Withdrawal\nagreed',  '#1a6bbd'),
    ('2018-11-15', 'Mass\nresignations',  '#b22222'),
    ('2019-03-29', 'Brexit\ndeadline 1',  '#1a6bbd'),
    ('2019-05-24', 'May\nresigns',         '#2e8b57'),
    ('2019-07-23', 'Johnson\nbecomes PM', '#2e8b57'),
    ('2019-09-09', 'Parliament\nprorogued', '#8b008b'),
    ('2019-09-24', 'SC: prorogation\nunlawful', '#8b008b'),
    ('2019-10-31', 'Brexit\ndeadline 2',  '#1a6bbd'),
    ('2019-12-12', 'Con. majority\n(Johnson)', '#2e8b57'),
    ('2020-01-31', 'UK leaves\nEU',       '#0a3d7a'),
    ('2020-12-31', 'Transition\nends',    '#0a3d7a'),
    ('2020-03-23', 'UK lockdown\n1',      '#b22222'),
    ('2020-11-05', 'UK lockdown\n2',      '#b22222'),
    ('2021-01-05', 'UK lockdown\n3',      '#b22222'),
]

# Company IDs for reference
"""
BH-56	Kings College London
BH-73	University College London
BH-34	UCL Institute of Education
BH-372	Centrepoint
BH-87	School of Oriental & African Studies (SOAS)
BH-47	Birkbeck, University of London
BH-225	Queen Mary University of London
BH-922	Royal College of Art
BH-1183	St Mungo's
BH-373	London Business School
BH-2319	Single Homeless Project
BH-2970	Arts University Bournemouth

==============================

accounting-finance
admin-clerical-secretarial
catering-and-hospitality
charity-voluntary
construction-trades
creative-design-arts-and-media
customer-service-support
domestic-help
education
energy-oil-and-gas
engineering
facilities-maintenance
graduate
healthcare-and-social-care
hr-and-recruitment
it-computing-software
legal
management-exec-consulting
manufacturing
marketing-advertising-pr
other-general
part-time-weekend
property
sales
scientific-qa
transport-logistics-warehouse
travel-tourism
unknown
wholesale-and-retail

"""

#####################################################################################################################

def _get_uk_university_holidays(period_start, period_end):
    """Return (holiday_periods, bank_holidays) for UK universities within the plot date range.

    holiday_periods : list of (start: date, end: date, label: str)
        Approximate term-break windows (Christmas, Easter, Summer).
    bank_holidays   : list of date
        England & Wales bank holidays.
    """
    def _easter(year):
        # Anonymous Gregorian algorithm
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = (h + l - 7 * m + 114) % 31 + 1
        return date(year, month, day)

    def _first_monday(year, month):
        d = date(year, month, 1)
        return d + timedelta(days=(7 - d.weekday()) % 7)

    def _last_monday(year, month):
        last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        return last - timedelta(days=last.weekday())

    p_start = date.fromisoformat(period_start)
    p_end   = date.fromisoformat(period_end)

    holiday_periods = []
    bank_holidays   = []

    for year in range(p_start.year - 1, p_end.year + 2):
        easter = _easter(year)

        # Typical UK university term breaks
        holiday_periods += [
            (date(year, 12, 20), date(year + 1, 1,  6), 'Christmas Break'),
            (easter - timedelta(14), easter + timedelta(14),  'Easter Break'),
            (date(year, 7,  1), date(year, 9, 20),            'Summer Break'),
        ]

        # England & Wales bank holidays
        bank_holidays += [
            date(year, 1, 1),           # New Year's Day
            easter - timedelta(2),       # Good Friday
            easter + timedelta(1),       # Easter Monday
            _first_monday(year, 5),      # Early May Bank Holiday
            _last_monday(year, 5),       # Spring Bank Holiday
            _last_monday(year, 8),       # Summer Bank Holiday
            date(year, 12, 25),          # Christmas Day
            date(year, 12, 26),          # Boxing Day
        ]

    holiday_periods = [(s, e, lbl) for s, e, lbl in holiday_periods if s <= p_end and e >= p_start]
    bank_holidays   = [d for d in bank_holidays if p_start <= d <= p_end]
    return holiday_periods, bank_holidays


#####################################################################################################################

def main():

    # Derive reference range from the dataset for the current company/transaction type
    if company_id != 'ALL':
        ref_bounds = ddb.sql(f"""
                SELECT MIN(pr.Point), MAX(pr.Point)
                FROM PaymentsReceipts pr
                    LEFT JOIN Companies c ON pr.CompanyID = c.ID
                WHERE c.ID = '{company_id}' AND pr.tranType = '{transaction_type}'
                """).fetchall()[0]
    else:
        ref_bounds = ddb.sql(f"""
                SELECT MIN(pr.Point), MAX(pr.Point)
                FROM PaymentsReceipts pr
                WHERE pr.tranType = '{transaction_type}'
                """).fetchall()[0]
    reference_start = str(ref_bounds[0])
    reference_end   = str(ref_bounds[1])
    print(f"Reference range: {reference_start} to {reference_end}")

    if company_id != 'ALL':
        avg_amount = ddb.sql(f"""
                SELECT AVG(pr.Amount) as Amount
                FROM Points p
                    LEFT OUTER JOIN PaymentsReceipts pr ON p.Point = pr.Point
                    left outer join Companies c ON pr.CompanyID = c.ID
                WHERE c.ID = '{company_id}' AND pr.tranType = '{transaction_type}'
                    AND pr.Point BETWEEN '{reference_start}' AND '{reference_end}'
                """).fetchall()[0][0]
        raw_data = ddb.sql(f"""
                SELECT p.Point, SUM(pr.Amount)/{avg_amount} as Amount
                FROM Points p
                    LEFT OUTER JOIN PaymentsReceipts pr ON p.Point = pr.Point
                    left outer join Companies c ON pr.CompanyID = c.ID
                WHERE c.ID = '{company_id}' AND pr.tranType = '{transaction_type}'
                    AND pr.Point BETWEEN '{reference_start}' AND '{reference_end}'
                GROUP BY p.Point, c.Company, c.ID
                """)
    else:
        avg_amount = ddb.sql(f"""
                SELECT AVG(pr.Amount) as Amount
                FROM Points p
                    LEFT OUTER JOIN PaymentsReceipts pr ON p.Point = pr.Point
                    left outer join Companies c ON pr.CompanyID = c.ID
                WHERE pr.tranType = '{transaction_type}'
                    AND pr.Point BETWEEN '{reference_start}' AND '{reference_end}'
                """).fetchall()[0][0]
        raw_data = ddb.sql(f"""
                SELECT p.Point, SUM(pr.Amount)/{avg_amount} as Amount
                FROM Points p
                    LEFT OUTER JOIN PaymentsReceipts pr ON p.Point = pr.Point
                    left outer join Companies c ON pr.CompanyID = c.ID
                WHERE pr.tranType = '{transaction_type}'
                    AND pr.Point BETWEEN '{reference_start}' AND '{reference_end}'
                GROUP BY p.Point
                """)
                    
    stddev_amount = raw_data.std('Amount').fetchall()[0][0]
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
        vals = [x[1] for x in data]  # Extract Amounts from tuples
        if len(vals) < min_points:  # Option A: insufficient window — emit NaN rather than a misleading value
            results.append((point[0], point[1], float('nan')))
            min_points_failures.append(datepoint)
        else:
            apen = CalculateApEn(vals, run_length, r)
            results.append((point[0], point[1], apen))

    print(f"DatePoint, {results}")



    # Compute smoothed Amount on the full dataset first to avoid edge effects at display boundaries
    window = int(max(1, smoothing_window))
    all_amounts = np.asarray([row[1] if row[1] is not None else 0.0 for row in results], dtype=float)
    if window > 1 and len(all_amounts) > 0:
        kernel = np.ones(window) / window
        smoothed_all = np.convolve(all_amounts, kernel, mode='same')
        # Fix edges: replace convolution boundary artefacts with a centred slice
        half = window // 2
        for i in range(half):
            smoothed_all[i] = np.mean(all_amounts[:i + half + 1])
            smoothed_all[-(i + 1)] = np.mean(all_amounts[-(i + half + 1):])
    else:
        smoothed_all = all_amounts.copy()

    # Prepare data for plotting — filter to display window here, not in the calculation loop
    p_start = datetime.fromisoformat(period_start)
    p_end   = datetime.fromisoformat(period_end)
    dates = []
    apen_values = []
    amount_values = []
    smoothed_amounts = []
    for idx, row in enumerate(results):
        try:
            dt = datetime.fromisoformat(str(row[0]))
        except Exception:
            dt = row[0]
        if dt < p_start or dt > p_end:
            continue
        dates.append(dt)
        apen_values.append(row[2])
        amount_values.append(row[1] if row[1] is not None else 0.0)
        smoothed_amounts.append(smoothed_all[idx])
    smoothed_amounts = np.asarray(smoothed_amounts, dtype=float)


    # Plot line graph with Points on x-axis and Amount on secondary y-axis
    fig, ax_apen = plt.subplots(figsize=(12, 7))
    ax_amount = ax_apen.twinx()

    # --- UK university holiday shading ---
    _HOLIDAY_STYLE = {
        'Christmas Break': '#aed6f1',
        'Easter Break':    '#a9dfbf',
        'Summer Break':    '#fad7a0',
    }
    holiday_periods, bank_holidays = _get_uk_university_holidays(period_start, period_end)
    added = set()
    if show_holidays:
        for h_start, h_end, label in holiday_periods:
            ax_apen.axvspan(datetime(h_start.year, h_start.month, h_start.day),
                            datetime(h_end.year,   h_end.month,   h_end.day),
                            alpha=0.25, color=_HOLIDAY_STYLE.get(label, '#cccccc'), zorder=0)
            added.add(label)
        for bh in bank_holidays:
            ax_apen.axvline(datetime(bh.year, bh.month, bh.day),
                            color='#888888', linewidth=0.6, alpha=0.4, linestyle=':', zorder=1)

    # Compute visible failures here so it's available for both the axvline loop and the legend
    visible_failures = [d for d in min_points_failures
                        if p_start <= datetime.fromisoformat(str(d)) <= p_end]

    # Mark dates where min_points guard fired
    for fail_date in visible_failures:
        try:
            fd = datetime.fromisoformat(str(fail_date))
        except Exception:
            fd = fail_date
        ax_apen.axvline(fd, color='red', linewidth=1.0, alpha=0.6, linestyle='--', zorder=3)

    # ApEn line (left axis)
    line_apen, = ax_apen.plot(dates, apen_values, marker=None, linestyle='-', color='C0', linewidth=2.5, label='ApEn', zorder=5)
    ax_apen.set_ylabel('Approximate Entropy (ApEn)', color='C0')
    ax_apen.tick_params(axis='y', labelcolor='C0')

    # Amount line (right axis) — use dashed line or bars as preferred
    if show_amount:
        line_amt, = ax_amount.plot(dates, amount_values, marker=None, linestyle='-', color='C1', alpha=0.35, label='Value')
    else:
        line_amt, = ax_amount.plot([], [], linestyle='-', color='C1', alpha=0.35, label='Value')
    ax_amount.set_ylabel('Value', color='C1')
    ax_amount.tick_params(axis='y', labelcolor='C1')

    # Smoothed Amount line (right axis)
    if show_smoothed:
        line_amt_smoothed, = ax_amount.plot(dates, smoothed_amounts, marker=None, linestyle='-', color='#8b0000', linewidth=1.0, alpha=0.9, label=f'Value (MA{window})')
    else:
        line_amt_smoothed, = ax_amount.plot([], [], linestyle='-', color='#8b0000', linewidth=1.0, alpha=0.9, label=f'Value (MA{window})')

    # Widen ApEn y-axis so small variations look less jagged
    valid_apen = [v for v in apen_values if v is not None and not np.isnan(v) and not np.isinf(v)]
    if valid_apen:
        apen_lo, apen_hi = min(valid_apen), max(valid_apen)
        apen_pad = max(apen_hi - apen_lo, 0.01)
        ax_apen.set_ylim(apen_lo - apen_pad, apen_hi + apen_pad)

    # x-axis formatting
    ax_apen.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_apen.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')

    ##=========================================================================

    # --- Brexit / COVID event markers ---
    y_min, y_max = ax_apen.get_ylim()
    y_range = y_max - y_min
    # Place labels in the lower half to stay clear of the upper-left legend and title.
    # Four staggered levels; assign greedily to avoid adjacent events sharing the same level.
    label_y_positions = [
        y_min + 0.38 * y_range,
        y_min + 0.26 * y_range,
        y_min + 0.14 * y_range,
        y_min + 0.02 * y_range,
    ]
    p_start_dt = datetime.fromisoformat(period_start)
    p_end_dt   = datetime.fromisoformat(period_end)
    visible_events = [(d, lbl, col) for d, lbl, col in KEY_EVENTS
                      if p_start_dt <= datetime.fromisoformat(d) <= p_end_dt]
    if show_events:
        assigned_levels = []
        for idx, (event_date, label, color) in enumerate(visible_events):
            dt = datetime.fromisoformat(event_date)
            ax_apen.axvline(dt, color=color, linewidth=1.2, linestyle='--', alpha=0.8, zorder=2)
            # Pick the level least recently used among the neighbours
            level = idx % len(label_y_positions)
            if len(assigned_levels) >= 1 and assigned_levels[-1] == level:
                level = (level + 1) % len(label_y_positions)
            if len(assigned_levels) >= 2 and assigned_levels[-2] == level:
                level = (level + 1) % len(label_y_positions)
            assigned_levels.append(level)
            ax_apen.text(dt, label_y_positions[level], label,
                         color=color, fontsize=6.5, ha='center', va='bottom',
                         rotation=0, bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.75, ec='none'))

    # Combine legends — data lines + holiday patches
    holiday_patches = [
        mpatches.Patch(facecolor='#aed6f1', alpha=0.6, label='Christmas Break'),
        mpatches.Patch(facecolor='#a9dfbf', alpha=0.6, label='Easter Break'),
        mpatches.Patch(facecolor='#fad7a0', alpha=0.6, label='Summer Break'),
        mpatches.Patch(facecolor='#888888', alpha=0.4, label='Bank Holiday'),
    ] if show_holidays else []
    from matplotlib.lines import Line2D
    extra_handles = []
    if visible_failures:
        extra_handles = [Line2D([0], [0], color='red', linewidth=1.0, linestyle='--', alpha=0.6, label=f'Insufficient window (<{min_points} pts)')]
    all_handles = [line_apen, line_amt, line_amt_smoothed] + holiday_patches + extra_handles
    ax_apen.legend(all_handles, [h.get_label() for h in all_handles], loc='upper left', fontsize=7, ncol=2)

    plt.title(f"ApEn and Values over Points (m={run_length}, r={r:.4f}, filtering={filtering_level})"
              + (f' for Category {company_id}' if company_id != 'ALL' else ' for All Categories')
              + (f" Window: {window_days} days (~{window_days // 7} pts), Display: {period_start} to {period_end}"),
              fontsize=6)
    ax_apen.grid(True, which='both', axis='both', alpha=0.4)
    fig.text(0.5, 0.01, f'Dataset: {dataset_file}', ha='center', va='bottom', fontsize=4, color='#888888')
    fig.tight_layout()
    now_str = datetime.now().strftime('%Y%m%dT%H%M%S')  # e.g. 20250924T153045
    plt.savefig(f"../Output/apen_amount_plot_{now_str}.png", dpi=300)
    plt.close()

    print(f"Saved plot to apen_amount_plot_{now_str}.png and computed {len(results)} points.")

####################################################################################################################
# Approximate Entropy Calculation
####################################################################################################################
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


######################################################################################################################
if __name__ == "__main__":
    main()
