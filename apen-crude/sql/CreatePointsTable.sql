CREATE TABLE Points 
(
    Point DATETIME PRIMARY KEY
    ,WeekNo INT
    ,YearNo INT
);

-- 2018-01-05 is Friday
WITH RECURSIVE DateTable AS
(
SELECT 
    CAST('2018-01-05' AS DATETIME) AS Point
    ,1 as WeekNo
    ,2018 as YearNo
UNION ALL 
SELECT 
    DATE_ADD(Point, INTERVAL 1 WEEK) as Point 
    ,WEEKOFYEAR(DATE_ADD(Point, INTERVAL 1 WEEK)) as WeekNo
    ,YEAR(DATE_ADD(Point, INTERVAL 1 WEEK)) as YearNo
FROM DateTable
WHERE 
    DATE_ADD(Point, INTERVAL 1 WEEK) <= '2022-12-31'
)
INSERT INTO Points (Point, WeekNo, YearNo) 
SELECT Point, WeekNo, YearNo FROM DateTable;
