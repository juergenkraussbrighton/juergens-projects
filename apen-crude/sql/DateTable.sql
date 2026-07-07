CREATE TABLE Dates 
(
    Point DATETIME
    ,WeekNo INT
    ,Year INT
);

WITH RECURSIVE DateTable AS
(
SELECT 
    CAST('2018-01-01' AS DATETIME) AS Point
    ,1 as WeekNo
    ,2018 as Year
UNION ALL 
SELECT 
    DATE_ADD(Point, INTERVAL 1 WEEK) 
    ,WEEKOFYEAR(Point) as WeekNo
    ,YEAR(Point) as Year
FROM DateTable
WHERE 
    Point <= '2022-12-31'
)
INSERT INTO Dates (Point, WeekNo, Year) 
SELECT Point, WeekNo, Year FROM DateTable;
