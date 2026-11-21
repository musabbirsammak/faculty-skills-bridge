# Methodology

How the starter catalogue was built, how courses are classified, and how matching works. This describes the first version honestly, including its limits.

## 1. Matching
`catalog/matching.py` is plain Python, so the method can be read and tested on its own.

- Each course lists **core** skills (weight 3) and **supporting** skills (weight 1).
- A teacher's level gives credit: *can teach it* 1.0, *use it regularly* 0.7, *familiar* 0.35.
- A closely **related** skill gives up to 0.35 times its level (e.g. Software testing towards Model evaluation).
- **Match** = weighted share of the course's skills the teacher covers.
- **Ready now**: match of 70% or more, with every core skill at least 0.6. **Short preparation**: 45% or more. **Stretch**: 25% or more.
- Within each tier, courses are ordered by **impact**, then by match.
- **Learning priorities** add up impact × weight × missing share for each missing skill, across short-preparation and stretch courses.

## 2. The starter catalogue
The first catalogue was put together by hand as an informed starting point. It is not measured from data.

- **Courses**: 38 computing courses (16 established, 22 recent) and 26 business courses (16 established, 10 recent). Established courses reflect what typical departments teach; "recent" marks subjects departments are adding in the AI era. Both choices are judgement calls.
- **Course names** follow the style of the ACM/IEEE curriculum guidelines (CS2023 for computing).
- **Skills**: 106 skills. Each has one standard name and several alternative names used by search, the same structure ESCO uses for skills. The skills are not yet linked to official ESCO entries; the `import_esco` command can link and extend them from ESCO's published data.
- **Related skills**: each skill has one or two related skills, chosen by judgement.
- **Course–skill links**: each course has 1–3 core and 1–4 supporting skills, based on what teaching it usually requires. They were not extracted from real syllabi.

## 3. Impact ratings (1–5)
Ratings estimate how much a subject's value will grow over the next five years. Where possible they are anchored to the **WEF Future of Jobs Report 2025**, which names AI and big data, networks and cybersecurity, and technological literacy as the three fastest-growing skill areas to 2030, with environmental stewardship newly in the top ten.

- **5**: central to the fastest-growing areas
- **4**: closely tied to a growing area, or a foundation for one
- **3**: stable, foundational or more specialised

No course was rated 1 or 2 without evidence. Each course shows its rating, its reason and its source; ratings without a direct source are marked "Starter rating; review locally". The WEF data is global and about skills and jobs, not courses or any one country; matching courses to WEF skill areas was a judgement.

## 4. Fields and areas (classification)
- **Area**: each course's area is the **UNESCO ISCED-F 2013 detailed field** that best describes its content, e.g. *0613 Software and applications development and analysis*, *0411 Accounting and taxation*.
- **Field of study**: the broad ISCED-F field, set automatically from the area code. Courses are classified by content, so statistics courses sit under *0542 Statistics* and economics under *0311 Economics*, whichever department teaches them. Mixed subjects use ISCED-F's inter-disciplinary codes (*0688*, *0488*).
- ISCED-F was chosen because UNESCO, the OECD and Eurostat use it to classify education, which makes catalogues comparable across universities and countries.

## 5. Skill families
Families group skills for browsing only and have no effect on matching. They were chosen by hand in three layers: disciplines following the ISCED-F broad fields; finer groups where starter data exists (computing along the main CS2023 areas, business along the usual programme areas); and cross-cutting families (mathematics and statistics, people and teaching, sustainability). An "Other" family holds skills that don't fit yet. Families are not an official taxonomy.

## 6. Privacy
Skill profiles are visible only to their owner. Heads, deans and leadership see totals for the units their role allows, and any number below `PRIVACY_MIN_GROUP` (default 3) is hidden.

## 7. Known limits and how to strengthen the data
The first version had no faculty review, no real syllabi and no local labour-market data. Recommended steps for each university:
1. **Faculty review**: 5–8 colleagues rate impact and check skill links per course, over two rounds (a simple Delphi process).
2. **Real syllabi**: tag your own syllabi against ESCO skills.
3. **Local demand**: count skills in 100–200 local job postings.
4. **Usage feedback**: "Makes sense / Doesn't fit" answers show where links are wrong.
