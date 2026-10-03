# Data guide

Learn Signal needs a small decision model, not a dataset: the options you could choose, the future scenarios that matter to the choice, the net payoff of each option in each scenario, and the studies you are considering. You can upload it, type it in, or have an AI draft it from your notes. The **What data do I need?** panel on **1 · Add your data** offers a simple Excel example, a complete Excel example and a CSV example. All examples are fictional.

## Before you start

1. **Choose one unit and one time horizon** for every payoff and study cost, for example "NOK contribution over the next 12 months". Higher must always be better.
2. **Define scenarios that cannot both be true and together cover what could happen.** If two uncertainties interact (demand and competitor response, say), make joint scenarios such as "High demand, no competitor response".
3. **Use net payoffs.** Each payoff includes that option's own costs but not the cost of research; studies are costed separately.
4. **Leave unknown numbers blank.** A blank is unknown, not zero. Results wait until priors and payoffs are filled in.

## Route 1: one simple table (Excel or CSV)

One row per decision option × future scenario. Use **Simple business tables** as the file layout.

| Decision option | Future scenario | Scenario probability | Net payoff | Assumption or evidence note |
|---|---|---|---|---|
| Launch | Higher demand | 0.4 | 140000 | Planning assumption |
| Launch | Lower demand | 0.6 | -60000 | Planning assumption |
| Pilot | Higher demand | 0.4 | 50000 | Planning assumption |
| Pilot | Lower demand | 0.6 | -10000 | Planning assumption |
| Hold | Higher demand | 0.4 | 0 | Planning assumption |
| Hold | Lower demand | 0.6 | 0 | Planning assumption |

- **Decision option** and **Future scenario** are required in every row. You need at least two of each.
- **Scenario probability** is the prior for that scenario. It must be the same in every row of the scenario, and the distinct scenarios must total exactly 1. Write `0.4` or `40%`, not `40`. Nothing is rescaled for you.
- **Net payoff** and **Assumption or evidence note** are optional; blank payoffs stay unknown.
- Your own column names work: the app suggests a match from the headings, and you confirm or change each one. A source column can fill only one role.
- In the app you also enter the business question, the **payoff unit** and the **time horizon**, and choose whether text numbers use dot (`1.5`) or comma (`1,5`) decimals. A number with the other separator is rejected rather than guessed.

The simple table carries no studies. Add them afterwards on **2 · Edit & review**, or use the complete workbook.

## Route 2: the complete project workbook

The workbook has one sheet per part of the model, linked by short reference codes (`S1`, `A1`, `T1`, ...). **5 · Export** writes the current case in this format, so the easiest way to build one is to download it, edit it in Excel and re-import it with **Complete project workbook** as the layout.

| Sheet | One row per | Key columns |
|---|---|---|
| Case | the case | Case brief |
| Scope | the case | Payoff unit, Time horizon |
| Future scenarios | scenario | Reference, Name, Probability (0 to 1), Notes, Source reference |
| Decision options | option | Reference, Name |
| Payoffs | option × scenario | Decision reference, Scenario reference, Net payoff, Notes, Source reference |
| Research studies | study | Reference, Name, Research cost, Description, Source reference |
| Study results | study × scenario × result | Study reference, Scenario reference, Study result, Probability (0 to 1) |
| Questions | question | Reference, Name |
| Answers | question × scenario | Question reference, Scenario reference, Answer |
| Sources | source | Reference, Source title, Source URL, Notes |

**Study results are the probability of each result if a scenario were true**, P(result | scenario), not the probability of a scenario after seeing a result. For a study with results "positive" and "negative", each scenario needs one row per result, and the two probabilities total 1 within that scenario. In the demo the structured test reads positive with probability 0.8 if demand is higher and 0.2 if it is lower.

**Questions and answers** describe an uncertainty you could resolve perfectly. Each scenario gets the answer that would be true in it; scenarios sharing an answer cannot be told apart by that question.

Sheets named "Read me" or "Instructions" are skipped, and result sheets in an exported workbook are ignored on import. Review signatures are never imported from Excel.

## Route 3: manual entry or an AI draft

**Enter manually** starts a blank case with two scenarios and two options for you to edit on **2 · Edit & review**. **Use your AI** gives you a prompt containing the exact JSON schema and your notes; paste it into an AI you choose and paste the JSON back. The app makes no AI call itself. The AI is told to leave unknown numbers as `null`, and an import that changes the brief is refused.

Saved projects (`learn-project.json` from **5 · Export**) are restored under **Restore a saved project**. A saved review is kept only if its fingerprint still matches the data.

## What is rejected

Each problem is reported with the sheet, row and column where possible, and the current case is left unchanged:

- `.xls` and other formats (save as `.xlsx`), or a CSV that is not UTF-8;
- formula cells without a saved result (recalculate and save in Excel first) and Excel error cells;
- blank or duplicate headings, or rows with more values than headings;
- probabilities outside 0 to 1, priors or result probabilities that do not total 1, TRUE/FALSE or text in number columns, NaN or infinity;
- duplicate option × scenario rows, references to a missing scenario, option, study, question or source, duplicate reference codes;
- source links that are not public `http(s)` addresses (use a blank URL for internal material).

## Data limits

**On your own computer there are no built-in limits.** Learn Signal reads any number of sheets, rows, columns, cells, scenarios, options, studies and results; the computer's memory and processor are the limit. Every calculation is exact and grows with options × scenarios × study results, never combinatorially, so a model with a thousand scenarios still calculates in a couple of seconds. The upload cap is 10,000 MB, set in `.streamlit/config.toml`, by the launchers (`LEARNSIGNAL_MAX_UPLOAD_MB`) and in the Dockerfile. If a file is too big for the computer's memory, the app says so instead of crashing. Very long result tables show their first 50,000 rows on screen with a note; the ZIP export contains every row, as does the Excel workbook up to Excel's own 1,048,576 rows per sheet.

**The public demo** (`SIGNAL_PUBLIC=1`, as on the public Signal Hub) protects a shared server with hard caps, all defined in `src/learnsignal/limits.py`. A capped message says it is a demo limit; the downloaded app has none.

| Demo cap | Value |
|---|---|
| Upload size (spreadsheets in total, or one JSON file) | 50 MB |
| Unpacked workbook size, files inside a workbook | 200 MB, 1,000 |
| Workbook sheets | 30 |
| Rows and columns per sheet | 10,000 and 80 |
| Cells across all files | 250,000 |
| Pasted AI reply, notes pasted into the AI prompt | 1,000,000 and 35,000 characters |
| Scenarios, options, payoffs | 30, 12, 360 |
| Studies, results per study, study-result rows | 12, 10, 3,600 |
| Questions, answers, sources | 20, 600, 100 |

Text fields keep fixed lengths everywhere because they are labels, not data: for example 150 characters for a scenario or option name, 2,500 for the case brief and 1,000 for a note. The JSON schema in the AI prompt lists each one. Payoffs and costs must lie within ±10¹² of the chosen unit.
