


CREATE TABLE JobIndices (
    id BIGINT PRIMARY KEY, 
    JobsIndex DOUBLE, 
    YearNo BIGINT, 
    WeekNo BIGINT, 
    JobCategoryId BIGINT REFERENCES JobCategories(id)
);
INSERT INTO 
    JobIndices (id, JobsIndex, YearNo, WeekNo, JobCategoryId)
SELECT 
    row_number() OVER() as id
    ,r.v4_1 as JobsIndex
    ,r."calendar-years" as YearNo
    ,CAST(REPLACE(r."week-number", 'week-', '') as BIGINT) as WeekNo
    ,j.id as JobCategoryId
FROM 
    RawData r JOIN JobCategories j ON j.JobCategory = r.AdzunaJobsCategory
WHERE 
    r.v4_1 IS NOT NULL
;
