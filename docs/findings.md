# Data findings

What the data actually looks like, found by profiling it. Updated as the project goes.

**Dataset:** LegiScan, Oklahoma 2026 Regular Session (session_id 2219), downloaded Nov 1, 2026.

## Counts

| Object | Count | Notes |
|---|---|---|
| Bills | 6,008 | Includes bills carried over from 2025 |
| Roll calls | 8,604 | Committee and floor votes together |
| People | 154 | Oklahoma has 149 seats (101 House, 48 Senate), so about 5 people likely left or replaced someone mid-session |

The 154 people matched in two separate pulls (`getSessionPeople` and the dataset), which was the first consistency check.

## Vote types

Roll calls split by whether the description contains "committee":

| Type | Roll calls | Zero "nay" votes | % zero nays |
|---|---|---|---|
| Committee | 5,204 | 3,240 | 62.3% |
| Floor | 3,400 | 1,124 | 33.1% |

The "floor" group breaks down into different kinds of votes (top 15 descriptions shown, 3,376 of 3,400):

| Kind | Roll calls | Descriptions |
|---|---|---|
| Third reading | 2,760 | `House: THIRD READING` (1,552), `Senate: THIRD READING` (1,208) |
| Fourth reading | 371 | `House: FOURTH READING` (205), `Senate: FOURTH READING` (166) |
| Veto override | 111 | `VETO OVERRIDE NO EMERGENCY`, `WITHOUT EMERGENCY`, `WITH EMERGENCY` (both chambers) |
| Emergency clause | 41 | `House: EMERGENCY` |
| Procedural | 93 | `ADOPT`, `AMENDMENT`, `RECONSIDER`, `ADOPT RESOLUTION`, `ADOPT MOTION` |

**Takeaways**

- Floor votes are not mostly unanimous. My first guess, based on one 92–0 bill, was wrong.
- "At least one nay" does not mean a party split. Measuring that needs each vote joined to the legislator's party.
- Voting metrics like party unity should use final passage votes (third and fourth reading), not procedural motions.

## Field notes

Confirmed by reading downloaded files, not from memory.

**Roll call** (`vote/*.json`)
- `yea`, `nay`, `nv`, `absent`, `total` are numbers, and they add up: in the sample, 7 + 4 + 0 + 0 = 11 = `total`, and `votes[]` has 11 entries.
- `passed` is `1` or `0`, not true/false.
- `chamber` is `"S"` or `"H"`.
- `votes[]` holds `people_id`, `vote_id`, `vote_text`. Confirmed: `vote_id` 1 = Yea, 2 = Nay. Codes 3 and 4 not yet seen.
- Committee votes name the committee in `desc`, for example `"Senate: Revenue & Taxation Committee: DO PASS"`.

**Person** (`people/*.json`)
- `party_id` is a string (`"2"`) while `state_id` is a number. Types need casting in staging.
- `district` is a code like `"HD-037"` (House) or `"SD-001"` (Senate).
- `person_hash` changes when a person's details change. Useful for tracking party or district changes.
- `bio` is nested several levels deep: phone, office address, photo URL, official website.
- `opensecrets_id` and `bioguide_id` are empty (they are federal IDs).

**Bill** (`bill/*.json`)
- `change_hash` is present, as LegiScan's documentation says.
- `sasts` can include `"type": "Carry Over"` with the bill's ID in the previous session. HB1002 is `bill_id` 2049840 in 2026 and 1893053 in 2025.
- `subjects` was empty in the sample bill, so topic tags may need to come from somewhere else.
- `sponsors[]` can have two people with `sponsor_type_id` 1 (the House author and the Senate author).
- `progress[]` event codes line up with `history[]` dates in the sample: 1 = introduced, 9 = referred to committee, 10 = reported from committee, 2 = engrossed.
- `status: 2` matched "Engrossed, signed, to Senate" on the bill's `status_date`.
- `completed: 0` with session `sine_die: 1` means the bill never finished before the session ended.

## Party voting on final passage

How often each party voted "Nay" on final passage votes (third and fourth reading), counting only Yea and Nay votes.

| Party | Yea/Nay votes cast | Nays | % Nay |
|---|---|---|---|
| Republican | 179,446 | 16,718 | 9.3% |
| Democrat | 38,393 | 6,907 | 18.0% |

**Takeaways**

- Democrats voted "Nay" about twice as often as Republicans (18.0% vs. 9.3%).
- About 82% of these votes were cast by Republicans, roughly matching their share of seats. This served as a sanity check on the join.
- Only two parties appear. No other party cast final passage votes in this session.
- These are overall rates. They do not show whether the parties voted against each other on the same roll call. That needs a per-roll-call comparison (next step: `int_party_majority_position`).

**Query**

```sql
SELECT p.party,
       COUNT(*) AS votes_cast,
       SUM(CASE WHEN v.vote_text = 'Nay' THEN 1 ELSE 0 END) AS nays,
       ROUND(100.0 * SUM(CASE WHEN v.vote_text = 'Nay' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_nay
FROM analytics_staging.stg_votes v
JOIN analytics_staging.stg_roll_calls r ON r.roll_call_id = v.roll_call_id
JOIN analytics_staging.stg_people p     ON p.people_id    = v.people_id
WHERE r.vote_category = 'final_passage'
  AND v.vote_text IN ('Yea', 'Nay')
GROUP BY p.party
ORDER BY votes_cast DESC;
```

**Data quality checks passing (dbt, 18 of 18):** every roll call's vote rows match LegiScan's `total`; no legislator votes twice on one roll call; every vote links to a real roll call and a real person.

## Party-line votes

Of 3,131 final passage roll calls, **565 (18%) were party unity votes**: a majority of Republicans voted opposite a majority of Democrats (Yea and Nay only; definition adapted from [Voteview](https://voteview.com/articles/party_unity_scores)). The other 2,566 had both party majorities on the same side.

This is enough party-line votes to calculate a party unity score for each legislator. Built in `int_party_positions`.

## Party unity by legislator

Built in `legislator_party_unity` (marts). Party unity score = share of party-line votes (565 final passage roll calls) where the legislator voted with their party's majority. Legislators with fewer than 50 party-line votes are excluded from rankings to avoid small samples.

Lowest scores in the 2026 session ranged from 41.1% to about 75%, and included both Democrats and Republicans. A low score means the legislator often voted with the other party's majority; the data alone does not explain why. Next: list the specific bills where each legislator broke from their party.

## Open questions

- [ ] What do `vote_id` 3 and 4 mean? (Likely "NV" and "Absent"; confirm from `vote_text`.)
- [ ] Why did a House third reading total 99 instead of 101? Vacancies, or how totals are counted?
- [ ] How many of the 6,008 bills are carryovers from 2025?
- [ ] How often is `subjects` filled in across all bills?
- [ ] What exactly is "fourth reading" in Oklahoma's process? Confirm with the Legislature's own rules.