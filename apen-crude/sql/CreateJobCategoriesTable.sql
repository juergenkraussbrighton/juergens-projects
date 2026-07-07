
CREATE TABLE JobCategories 
(
    id BIGINT PRIMARY KEY, 
    JobCategory VARCHAR(255) UNIQUE
);

WITH JobCats AS (
    SELECT DISTINCT 
        AdzunaJobsCategory as JobCategory
    FROM 
        RawData 
)
INSERT INTO JobCategories (id, JobCategory)
SELECT  
    ROW_NUMBER() OVER() as id 
    ,JobCategory
FROM 
    JobCats
;