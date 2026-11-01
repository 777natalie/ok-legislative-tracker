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

## Open questions

- [ ] What do `vote_id` 3 and 4 mean? (Likely "NV" and "Absent"; confirm from `vote_text`.)
- [ ] Why did a House third reading total 99 instead of 101? Vacancies, or how totals are counted?
- [ ] How many of the 6,008 bills are carryovers from 2025?
- [ ] How often is `subjects` filled in across all bills?
- [ ] What exactly is "fourth reading" in Oklahoma's process? Confirm with the Legislature's own rules.