# Discord chat stats

Charts and summaries from a Discord conversation export. Nothing about who is in the
conversation is built in: the usernames come from the export, so the same scripts work
on anyone's. Each output is its own script; the shared code lives in `chatstats/`.

## Getting started

**1. Install Python**, version 3.12 or newer, from [python.org](https://www.python.org/downloads/).
To check what you have:

```
python --version
```

**2. Install the two libraries** the scripts need, from this folder:

```
pip install pandas matplotlib
```

If you use [uv](https://docs.astral.sh/uv/), `uv sync` does the same from the lockfile.

**3. Export the conversation.** These scripts read a CSV export of a Discord channel or
DM, made with the Discrub browser extension. Choose **CSV** as the export format. A long
conversation comes out as several numbered pages in the format `(group or dm)-page-NN`.
Bulk rename them to `page-NN` with one of the commands below, or keep the names and pass
`--pattern "*-page-*.csv"` to every script instead.

Run this from inside the folder holding the CSVs. It strips everything before `page-`,
leaves any other file alone, and does nothing if there is nothing to rename.

In PowerShell:

```powershell
Get-ChildItem -Filter *-page-*.csv | Rename-Item -NewName { $_.Name -replace '^.*-(page-\d+\.csv)$', '$1' }
```

In bash:

```bash
for f in *-page-*.csv; do [ -e "$f" ] || continue; mv -- "$f" "page-${f##*-page-}"; done
```

**4. Put the CSVs in a `data` folder**.

**5. Check it loaded.** Run the scripts from the project folder, since `data` is found
relative to where you run them. `overview.py` prints a summary and writes no chart,
which makes it the quickest test:

```
python overview.py
```

The first two lines say how much was read and who was found in it:

```
Loaded 39,072 messages from 79 file(s)
Users: triflicacid, megamoleys
```

If those look right, run any of the others. Each writes a PNG into `out/`:

```
python messages_per_day.py
python highlights.py
python topics.py
```

There is nothing to configure: the usernames come from the export. `config.toml` is
optional, and only sets each person's chart colour and any dates worth marking.

One option is worth setting if you are not in the UK. The export writes its times in
the timezone it was made in, and the scripts assume `Europe/London`, so pass your own
to get the days and hours right:

```
python daily_rhythm.py --tz America/New_York
```

Every script takes `--help`, and the sections below list what each one does and the
options it takes.

### If it does not work

**`No files matching 'page-*.csv' in ...`** — nothing was found to read. The message
prints the full path it looked in; check the CSVs are there, and see step 4 for the
name and `--dir`.

**`page-1.csv: missing columns [...]`** — a file was found but is not a Discrub message
export. Check you exported messages as CSV, and that no unrelated CSV is sitting in the
folder.

**A chart is empty or missing someone** — check the `Users:` line from step 5. Matching
ignores case, and `--users` narrows the list when an export holds more people than you
want on the chart.

## How the export is read

Pages are sorted by number, concatenated and deduplicated on message ID, so overlapping
pages do no harm.

Two quirks of the export the scripts work around:

- `Timestamp` is local wall clock truncated to the minute. Too coarse for reply times,
  where over half of all replies land in the same minute as the message they answer.
  The real send time is decoded from the message ID instead: a Discord snowflake's top
  42 bits are milliseconds since 1 January 2015. The column is only a fallback.
- Those times are written in whatever timezone the export was made in, not UTC. `--tz`
  says which, and is also the timezone the day and hour buckets follow. It defaults to
  `Europe/London`, so set it if that is not yours.

## Running everything

In PowerShell:

```powershell
$all = 'overview','highlights','calendar_heatmap','messages_per_day','message_length','volume_breakdown','conversation_duration','daily_rhythm','reply_times','initiators','last_word','messages_in_a_row','response_curve','nudges','questions','links','reactions','topics','distinctive_words'
foreach ($s in $all) { python "$s.py" }
```

In bash:

```bash
for s in overview highlights calendar_heatmap messages_per_day message_length volume_breakdown conversation_duration daily_rhythm \
         reply_times initiators last_word messages_in_a_row response_curve nudges questions links reactions topics distinctive_words; do
    python "$s.py"
done
```

`word_usage.py` is left out: it charts the words you name, so it needs `--words`.

## Shared arguments

Accepted by every script. The table in each section below lists only that script's own.

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `./data` | Folder holding the export CSVs. |
| `--pattern PATTERN` | `page-*.csv` | Glob used to find export pages in it. |
| `--users USERS [USERS ...]` | every username in the export | Usernames to use. Matching ignores case. |
| `--tz TZ` | `Europe/London` | Timezone of the export's wall clock times, and of the day and hour buckets. |
| `--config CONFIG` | `config.toml` | Optional file of key dates and per-username colours. |
| `--key-dates` | off | Mark the config's `key_dates` on the chart. |

## Who gets charted

Every script scans the export and charts every username it finds. The count loaded and
the names chosen are printed first:

```
Loaded 39,072 messages from 79 file(s)
Users: triflicacid, megamoleys
```

Matching ignores case, and a name spelled in more than one casing counts once, under
its most frequent spelling. `--users` narrows the list, which matters for a group chat:
left alone, everyone who ever spoke gets a line.

The order is `config.toml`'s for the users it names, then everyone else by how much
they said. It decides two charts that subtract the second user from the first: the
middle row of `topics.py` and the bottom panel of `conversation_duration.py`. Both are
drawn only when there are exactly two users.

## config.toml

Optional, as is each part of it. `--config` points at a different file. The file in
this repo is an example.

`key_dates` is the list `--key-dates` draws. An entry is a bare date, which gets a line
and nothing written beside it, or a `{ date = ..., label = ... }` table, which gets
both. Write dates unquoted, as `2026-09-19`; a time of day is accepted but dropped.
Order does not matter. The list must come above `[usernames]`, or TOML reads it as part
of that table.

`[usernames]` maps a username to a chart colour: anything matplotlib accepts, such as
`"#E8730C"`, `"orange"` or `"C4"`. Leave it `""` to set the user's place in the order
and let matplotlib pick. A name not in the export is ignored.

## Key dates

`--key-dates` works on every script, and does nothing but say so when the config lists
none.

On a date axis each date is a black vertical line through every panel, labelled at the
foot of the top one. Three charts have no date axis and mark them their own way:
`daily_rhythm.py` between its month columns, placed by how far through the month the
date falls; `distinctive_words.py` across the page, between the two rows nearest the
date; `calendar_heatmap.py` as an outlined day, named in the note under its title.
`response_curve.py`, `highlights.py` and `overview.py` have nothing to mark. A date
outside the export's range is left out.

```
python initiators.py --key-dates
```

## Colours

Each user keeps one colour in every chart, so a line, a shaded span and a bar for the
same person always agree. A colour in `config.toml` is theirs for good. Anyone else
takes one of matplotlib's, handed out in name order rather than in the order `--users`
lists them, so listing the same people the other way round cannot repaint them;
charting a different set of people still can, which is what pinning in the config is
for.

Three colours are never handed to a user: crimson for the combined total, dark slate
for quantities belonging to everyone, and the teal ramp on `daily_rhythm.py`.

## Output

Every chart is written to `out/`, created if it does not exist; `--out` changes where
each one goes. A chart's title names what is plotted and nothing else, with anything
needed to read it in small grey type underneath.

## overview.py

Prints a text summary and writes no chart.

Total messages, date range and author count, then a table per user: messages, words,
messages with an attachment, attachments, reactions, active days, share of all
messages, average words per message, messages per active day. Then each user's daily
mean and median, busiest day and silent days, a weekday breakdown and the busiest hour.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--csv CSV` | not saved | Also write the per-user table to this CSV. |

### Examples

```
python overview.py
python overview.py --csv per_user.csv
python overview.py --tz UTC
```

## highlights.py

Writes `out/highlights.png`, a card of headline numbers with no axes at all.

The upper part is shared: total messages and words, days with a message, longest
streak, longest silence, busiest day, conversations held and the size of a typical
one, the biggest conversation, the fastest 100 messages, the busiest hour and weekday,
links and attachments.

The lower part gives each user the same ten numbers in their own colour: messages,
words, conversations started, days sending the first message, typical reply time, how
often they spoke again after an hour unanswered, questions asked, links and
attachments, longest message, and three signature words. A signature word is one that
user says often and the others hardly ever. Links are ignored and apostrophes dropped,
so "it's" and "its" count as one word.

Every number is also printed to the terminal.

`--output-longest` writes each user's longest messages in full to `<username>.txt` in
the current folder, each headed by its rank, date, time and word count, longest first.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation. Affects only the biggest-conversation tile. |
| `--out OUT` | `out/highlights.png` | Output image. |
| `--output-longest [N]` | off | Also write each user's N longest messages to `<username>.txt`. N defaults to 10. |

### Examples

```
python highlights.py
python highlights.py --gap 4
python highlights.py --output-longest
python highlights.py --output-longest 25
python highlights.py --out highlights.svg
```

## calendar_heatmap.py

Writes `out/calendar_heatmap.png`.

Every day in the range as one square, coloured by its message count. Weeks run left to
right, weekdays top to bottom. All users are pooled.

The colour scale is logarithmic, since the busiest day can hold a hundred times what a
typical one does. A silent day is grey, which keeps it apart from the white of days
outside the range.

A ring marks the busiest day and a line under the grid the longest streak of days with
at least one message. The three longest streaks are printed to the terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/calendar_heatmap.png` | Output image. |

### Examples

```
python calendar_heatmap.py
python calendar_heatmap.py --tz UTC
python calendar_heatmap.py --out calendar.svg
```

## messages_per_day.py

Writes `out/messages_per_day.png`, a chart of three panels sharing one date axis.

**The main panel** is one line per user, plus a red line for the combined total.

Its y axis is a symmetrical log scale by default, since the busiest day can carry
thirty times a typical one. Symmetrical, so silent days still plot at zero instead of
vanishing the way they would on an ordinary log axis.

Each user's busiest days are dotted and labelled with the count and date. Stretches
where everyone was quiet are shaded grey; stretches where only one user was quiet are
shaded in their colour, unless they fall inside a shared silence the grey already
covers. The same peaks and silences are printed to the terminal.

**The middle panel** is the running total per user and for everyone together, always
linear whatever `--axis` says. Slope is the rate: a flat stretch is a silence.

**The lower panel** is each user's share of the period's messages, stacked out of 100%
with a dashed line at 50%. Periods in which nobody said anything are left blank.

`--metric words` rescales all three panels together, to words per day, cumulative
words and share of words.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/messages_per_day.png` | Output image; any extension matplotlib supports. |
| `--metric {messages,words}` | `messages` | Count messages, or the words inside them. |
| `--period {D,W,M}` | `D` | Bucket: day, week from Monday, or calendar month. |
| `--rolling ROLLING` | `0` | Rolling average over this many periods, over a faint raw line. 0 = unsmoothed. |
| `--axis {linear,log}` | `log` | Y axis scale; `log` is symmetrical, so silent days plot at zero. `--yscale` is an older spelling. |
| `--total {true,false}` | `true` | Draw the red combined line. |
| `--peaks PEAKS` | `5` | How many of each user's busiest periods to label. 0 = off. |
| `--peak-distance PEAK_DISTANCE` | 14 days, 4 weeks or 2 months | Minimum periods between two labelled peaks. |
| `--quiet QUIET` | `12` | How many of the longest shared quiet stretches to shade grey. 0 = off. |
| `--quiet-min QUIET_MIN` | `1` | Ignore shared quiet stretches shorter than this. |
| `--user-quiet USER_QUIET` | `6` | How many of each user's own quiet stretches to shade. 0 = off. |
| `--user-quiet-min USER_QUIET_MIN` | 2 days, 1 week or 1 month | Ignore solo gaps shorter than this. |
| `--quiet-threshold QUIET_THRESHOLD` | `5` | A period is quiet at or below this count; 0 = silent. Applies to the total for `--quiet`, to each user for `--user-quiet`. |
| `--csv CSV` | not saved | Also write the daily counts to this CSV, following `--metric`. |

### Examples

```
python messages_per_day.py
python messages_per_day.py --period W --rolling 4
python messages_per_day.py --axis linear
python messages_per_day.py --total false
python messages_per_day.py --metric words
python messages_per_day.py --metric words --period W
python messages_per_day.py --peaks 8 --quiet 5
python messages_per_day.py --peaks 0 --quiet 0 --user-quiet 0
python messages_per_day.py --quiet-threshold 0 --quiet 3 --user-quiet 3
python messages_per_day.py --user-quiet 5 --user-quiet-min 7
python messages_per_day.py --csv daily.csv --out chart.svg
```

## message_length.py

Writes `out/message_length.png`.

Counting messages says how much someone talked; this says how they talked. The mean
words per message, one point per period per user, with the middle 50% of individual
messages shaded behind each line.

The band is a quartile range, which keeps the skew visible: most messages are very
short, and a handful of long ones pull the mean above the median. Periods under
`--min-messages` are left blank.

`--text-only` is worth knowing about. Messages with no words are usually an image or a
link on its own, and users send very different numbers of them, so leaving them in
flatters whoever sends more.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/message_length.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--min-messages MIN_MESSAGES` | `10` | Leave a period blank below this many messages. |
| `--text-only` | off | Ignore wordless messages, usually an image or a bare link. |

### Examples

```
python message_length.py
python message_length.py --text-only
python message_length.py --period M
python message_length.py --min-messages 50
python message_length.py --out length.svg
```

## volume_breakdown.py

Writes `out/volume_breakdown.png`.

Words written is conversations held, times messages in each, times words in each
message. All four on one date axis, so a change in how much was said can be put down
to talking less often, shorter conversations, or shorter messages.

The top panel is words per period, one line per user. Under it are the three factors.
Conversations per period has a single line, being shared; the other two have one per
user. The three lower panels multiply back to the top one.

Every panel is a rolling average over a faint raw line. Each ratio is smoothed as one
window total over another, so the panels still multiply back. Words per message is
blank below `--min-messages`. The printed summary gives the two halves of the range
side by side.

See `messages_per_day.py` for daily counts and `message_length.py` for the spread of
individual messages.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation. Raising it gives fewer, larger ones. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--out OUT` | `out/volume_breakdown.png` | Output image. |
| `--min-messages MIN_MESSAGES` | `10` | Leave words per message blank below this many messages. |
| `--rolling ROLLING` | `4` | Smooth every panel over this many periods. 0 = raw. |

### Examples

```
python volume_breakdown.py
python volume_breakdown.py --gap 4
python volume_breakdown.py --rolling 0
python volume_breakdown.py --period M --rolling 0
python volume_breakdown.py --out breakdown.svg
```

## conversation_duration.py

Writes `out/conversation_duration.png`.

How long conversations last in time, where `volume_breakdown.py` measures them in
messages. Duration is first message to last.

The upper row is one chart per user, for the conversations that user started: the
median duration, with the middle half as a band, on a log axis since durations run
from a minute to most of a day. The lower panel is the difference between the two
medians in minutes, filled in the colour of whoever lasted longer. It needs exactly
two users and is left out otherwise.

Only conversations more than one person took part in are counted; the printed summary
says how many were left out. Each point is worked out afresh from every conversation
in its window, since a median does not average. Points under `--min-conversations` are
left blank.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation. Raising it joins them up. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--out OUT` | `out/conversation_duration.png` | Output image. |
| `--min-conversations MIN_CONVERSATIONS` | `5` | Leave a point blank below this many conversations. |
| `--rolling ROLLING` | `4` | Periods each point looks back over. 0 or 1 uses the period alone. |

### Examples

```
python conversation_duration.py
python conversation_duration.py --gap 4
python conversation_duration.py --min-conversations 8
python conversation_duration.py --period M --rolling 0
```

## reply_times.py

Writes `out/reply_times.png`.

The median time each user takes to reply, one point per period, on a log y axis, with
the middle 50% of that period's replies shaded behind each line. Periods under
`--min-replies` are left blank.

Counts only replies inside a conversation: a silence longer than `--gap` starts a new
conversation rather than counting as a slow reply, so every long wait is excluded by
design. For those, use `response_curve.py`.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation. Slower replies leave the chart. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--out OUT` | `out/reply_times.png` | Output image. |
| `--min-replies MIN_REPLIES` | `3` | Leave a period blank below this many replies. |

### Examples

```
python reply_times.py
python reply_times.py --gap 3
python reply_times.py --period M
python reply_times.py --min-replies 10
python reply_times.py --out replies.svg
```

## initiators.py

Writes `out/initiators.png`.

Three panels sharing one date axis.

The top is conversations started per period by each user, with running totals and
overall shares in the legend. The middle is each user's share of those starts, stacked
with a dashed line at 50%; empty periods are left blank.

The bottom is the same share for who sent the first message of the day. It needs no
definition of a conversation, so `--gap` does not move it. The day turns over at
`--day-start`, so a message at 1am belongs to the night before.

Starts are small numbers, so this chart is smoothed by default; `--rolling 0` gives
the raw view.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation, so what counts as starting one. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--out OUT` | `out/initiators.png` | Output image. |
| `--day-start DAY_START` | `5` | Local hour at which a new day begins, for the bottom panel. |
| `--rolling ROLLING` | `4` | Smooth the top panel over this many periods, and both shares over the same window. 0 = raw. |

### Examples

```
python initiators.py
python initiators.py --gap 4
python initiators.py --rolling 0
python initiators.py --day-start 4
python initiators.py --period M --rolling 0
python initiators.py --out starts.png
```

## last_word.py

Writes `out/last_word.png`.

The counterpart to `initiators.py`: who sent the final message of each conversation,
the one followed by `--gap` hours of silence. The upper panel is conversations ended
per period by each user, the lower each user's share of them.

The last word means being the one left without an answer. A conversation nobody
answered is ended by whoever started it.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation, so what counts as the last word. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--out OUT` | `out/last_word.png` | Output image. |
| `--rolling ROLLING` | `4` | Smooth the upper panel and the share over this many periods. 0 = raw. |

### Examples

```
python last_word.py
python last_word.py --gap 4
python last_word.py --period M --rolling 0
```

## messages_in_a_row.py

Writes `out/messages_in_a_row.png`.

How many messages each user sends in a row before someone else replies, averaged per
period. A run of messages by one person is a turn; 1 means strict back and forth.

The line is the window's messages over the window's turns, and is blank below
`--min-turns`.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/messages_in_a_row.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--min-turns MIN_TURNS` | `10` | Leave the line blank below this many turns. |
| `--rolling ROLLING` | `4` | Smooth the line over this many periods. 0 = raw. |

### Examples

```
python messages_in_a_row.py
python messages_in_a_row.py --rolling 0
python messages_in_a_row.py --period M --rolling 0
```

## response_curve.py

Writes `out/response_curve.png`.

Splits every handover at `--gap` into two panels, since on a single axis the common
case hides the rare one. Unlike `reply_times.py`, no handover is discarded.

The top panel is a survival curve for replies inside a conversation: the share still
unanswered after each elapsed time, on a log x axis, one line per responder. Each
line's 50% and 10% crossings are marked.

The bottom panel covers waits past `--gap`, grouped by length (2-3h, 3-6h, 6-12h,
12-24h, over 24h). The pale bar is every wait in the group; the solid bar over it is
those where the waiter nudged.

A footer repeats every handover from the waiting side: times waited, waits over an
hour, the median of those, and nudges sent.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--gap GAP` | `2.0` | Hours of silence that end a conversation, where the panels divide, and where the wait buckets begin. |
| `--out OUT` | `out/response_curve.png` | Output image. |
| `--nudge-hours NUDGE_HOURS` | `1.0` | Hours of no answer before speaking again counts as a nudge. |

### Examples

```
python response_curve.py
python response_curve.py --gap 4
python response_curve.py --nudge-hours 2
python response_curve.py --gap 6 --nudge-hours 3
python response_curve.py --out waiting.png
```

## nudges.py

Writes `out/nudges.png`.

A nudge is speaking again after `--hours` with still no answer. `response_curve.py`
totals them; this puts them on a date axis. The upper panel is nudges sent per period
by each user, the lower each user's share. Each nudge is dated by itself, not by the
start of the wait it belongs to.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/nudges.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--hours HOURS` | `1.0` | Hours of no answer before speaking again counts as a nudge. |
| `--rolling ROLLING` | `4` | Smooth the upper panel and the share over this many periods. 0 = raw. |

### Examples

```
python nudges.py
python nudges.py --hours 2
python nudges.py --rolling 0
python nudges.py --period M --rolling 0
```

## questions.py

Writes `out/questions.png`.

Questions asked per period by each user, with each user's share underneath. A question
is a message holding a question mark or worded as one.

The wording test keeps the count fair between someone who types the mark and someone
who does not. A message is worded as a question when it opens with a question word
("what", "why", "how are", "when do"), puts the verb before the subject ("do you",
"is it", "can we"), asks what the other person wants ("you wanna", "shall we", "any
plans"), or ends in a tag ("... is it", "... dont you", "... or", "... right"). The
patterns are narrow, so "how lovely", "which is nice" and "do it anyway" do not count;
they are `QUESTION_WORDING` in `chatstats/counts.py`. Links are removed first, since a
URL often carries a question mark.

It is a rule of thumb, not a reading of the message. Totals are printed to the terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/questions.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--rolling ROLLING` | `4` | Smooth the upper panel and the share over this many periods. 0 = raw. |

### Examples

```
python questions.py
python questions.py --rolling 0
python questions.py --period M --rolling 0
python questions.py --key-dates
```

## links.py

Writes `out/links.png`.

Links shared per period by each user, with each user's share underneath. Every URL
counts, so a message holding two links counts twice.

A handful of links a period is too few to read raw, so this chart is smoothed by
default.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/links.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--rolling ROLLING` | `4` | Smooth the upper panel and the share over this many periods. 0 = raw. |

### Examples

```
python links.py
python links.py --rolling 0
python links.py --period M --rolling 0
python links.py --out links.svg
```

## reactions.py

Writes `out/reactions.png`.

Reactions each user's messages received per period, with each user's share underneath.

The export records how many reactions a message got, not who gave them. In a two-person
conversation a line is best read the other way round: one user's line is the other
person reacting to them.

Reactions are rare, so this chart is smoothed by default. Totals are printed to the
terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/reactions.png` | Output image. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--rolling ROLLING` | `4` | Smooth the upper panel and the share over this many periods. 0 = raw. |

### Examples

```
python reactions.py
python reactions.py --rolling 0
python reactions.py --period M --rolling 0
python reactions.py --key-dates
```

## topics.py

Writes `out/topics.png`.

What each user talked about over time, from a list of topics and the words that belong
to each: one chart per user, side by side, with a heatmap under them of where two
differ. Nothing is worked out here; it counts the words the topic file says to count.

**The topic file** is `topics.toml` in the project folder. Each line is a topic name
and its words:

```toml
art = ["art", "artwork", "draw*", "sketch*"]
"seeing each other" = ["meet*", "visit*", "train", "london"]
```

A word matches whole and ignores case, so "art" does not match "start". A trailing `*`
matches any ending; a trailing `+` lets the last letter repeat, so `yay+` covers
"yaaay". A message counts once per topic it mentions, and links are ignored. Topics are
stacked in the order the file lists them.

**The upper panel** in each column is that user's mix: each topic's share of their own
topic mentions, out of 100%. It shows what took the place of what. Periods under
`--min-mentions` are left blank.

**The middle panel** is a heatmap, a row per topic and a column per period, each cell
one user's share of that topic minus the other's in percentage points. A cell takes
the colour of whoever gave the topic more of their talk, darker for a bigger gap, and
is white where they match; grey where either has too few mentions to compare. The
scale stops short of the largest gap, so one unusual period does not wash out the
rest. Needs exactly two users and is left out otherwise.

**The lower panel** is one line per user: the share of that user's messages mentioning
any listed topic, as a reminder that the list covers only part of what was said.

The columns share their vertical axes. The mix is a share of each user's own mentions,
so a wider band means the topic took up more of that person's talk, not that they
mentioned it more times.

The printed summary gives each user's total per topic and the month it peaked in.

Use `distinctive_words.py` to find words worth adding.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/topics.png` | Output image. |
| `--topics TOPICS` | `topics.toml` | The file of topic names and their words. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--min-mentions MIN_MENTIONS` | `10` | Leave a user's mix blank below this many of their topic mentions. |
| `--rolling ROLLING` | `4` | Take the mix and the coverage over this many periods. 0 = raw. |

### Examples

```
python topics.py
python topics.py --period M --rolling 0
python topics.py --topics my_topics.toml
python topics.py --rolling 8
```

## distinctive_words.py

Writes `out/distinctive_words.png`.

Lists the words that set each month apart from the rest of the history, with no list
of what to look for. A word appears under a month when it was said at least
`--min-ratio` times more often then than in every other month put together. Each row
is a month, the strongest word comes first, and the colour shows how strong.

A word counts once per message however often it is repeated, so one long list cannot
put a word on the chart by itself. Links are ignored and apostrophes dropped, so
"it's" and "its" count as one word. `--min-ratio` keeps filler out: a quiet month is
left short or empty rather than padded with words like "there".

Words are shown as typed, and the same lists are printed to the terminal with their
scores. Same calculation as the signature words on the highlights card, grouped by
period instead of by person.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/distinctive_words.png` | Output image. |
| `--period {D,W,M}` | `M` | How long each row covers. |
| `--top TOP` | `8` | The most words to list in each row. |
| `--min-uses MIN_USES` | `8` | Ignore a word appearing in fewer messages than this in the period. |
| `--min-ratio MIN_RATIO` | `3.0` | How many times more common than elsewhere a word must be. |

### Examples

```
python distinctive_words.py
python distinctive_words.py --top 12
python distinctive_words.py --min-ratio 2 --min-uses 5
python distinctive_words.py --period W
```

## daily_rhythm.py

Writes `out/daily_rhythm.png`.

Two heatmaps of when in the day and week the conversation happens, and whether that
changed over time: hour of day above, day of week below, both across the same periods.

Every column is normalised to its own period, so the cells are shares, not counts:
raw counts would restate the volume trend and bury the rhythm. A ring marks each
column's busiest row.

All users are pooled. People talking to each other share a clock, so splitting by user
gives near identical panels.

The printed summary compares the two halves of the range rather than the first and
last columns, which cover only a few days each.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--out OUT` | `out/daily_rhythm.png` | Output image. |
| `--period {D,W,M}` | `M` | Width of each column. Weeks give a finer but noisier picture. |

### Examples

```
python daily_rhythm.py
python daily_rhythm.py --period W
python daily_rhythm.py --tz UTC
python daily_rhythm.py --out rhythm.svg
```

## word_usage.py

Writes `out/word_usage.png`, a single file holding one panel per word.

Each panel is how often each user said that word or phrase over time, with their
totals in the panel title. Panels sit in a grid of up to three columns, sharing one
date axis and one legend, each keeping its own y axis so a common word does not
flatten a rare one. With more than one word, the first panel adds them all together.

Matching ignores case and matches whole words, unless `--partial`. A trailing `*`
matches any ending, so `draw*` counts "drawing". A trailing `+` lets the last letter
repeat, so `hai+` counts "haiiii" but not "hair". Words joined by `|` are counted
together in one panel, so `"mum|mom|mother"` is a single line — quote it, or the shell
reads the bar as a pipe. Phrases match across any whitespace.

Produces nothing unless `--words` is given. Also prints totals per word and user, with
uses per 1,000 messages so users of very different volumes can be compared.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--words WORDS [WORDS ...]` | empty | Words or phrases to chart, one panel each. Quote anything with a space. Required. |
| `--period {D,W,M}` | `W` | Bucket: day, week from Monday, or calendar month. |
| `--mode {count,messages}` | `count` | Count every occurrence ("love love love" is three), or messages containing the word. |
| `--partial` | off | Match inside longer words too, so "love" also hits "gloves". |
| `--rolling ROLLING` | `0` | Rolling average over this many periods, over a faint raw line. 0 = unsmoothed. |
| `--out OUT` | `out/word_usage.png` | Output image. |
| `--columns COLUMNS` | up to 3 | Panels per row. |
| `--csv CSV` | not saved | Also write the counts to this CSV, one column per word and user. |

### Examples

```
python word_usage.py --words dear love
python word_usage.py --words "love you" --period M
python word_usage.py --words love --partial
python word_usage.py --words sorry --mode messages
python word_usage.py --words love --rolling 4
python word_usage.py --words "mum|mom|mother" "dad|father"
python word_usage.py --words dear love sorry "miss you" --columns 2
python word_usage.py --words dear love --out words.svg --csv words.csv
```

## Project layout

```
overview.py            printed summary, no chart
highlights.py          one card of headline numbers
calendar_heatmap.py    every day as a square, coloured by messages
messages_per_day.py    messages per day, cumulative, and share
message_length.py      average words per message over time
volume_breakdown.py    words split into conversations, their size and message length
conversation_duration.py  how long conversations last, by who started them
daily_rhythm.py        when in the day and week the messages land
reply_times.py         median reply time inside a conversation
initiators.py          who opens the conversation, and the day
last_word.py           who sends the last message of a conversation
messages_in_a_row.py   messages sent before someone else replies
response_curve.py      replying in a conversation against waiting for one
nudges.py              nudges sent over time
questions.py           questions each user asked
links.py               links shared over time
reactions.py           reactions each user's messages received
topics.py              what each user talked about, from topics.toml
distinctive_words.py   the words that set each month apart
word_usage.py          uses of a word over time

chatstats/
    loading.py         reads the CSVs, resolves timestamps and count columns
    periods.py         day, week and month bucketing, and the shared date axis
    formatting.py      durations and dates written as text
    counts.py          per day tallies, per period statistics, word matching
    peaks.py           finding peaks and quiet runs
    conversations.py   turns, handovers, reply statistics, printed summaries
    plotting.py        colours, ramps, saving, legends, the shared renderers
    summary.py         the overview tables
    topics.py          reading topics.toml and counting its words
    cli.py             shared arguments and the common entry point
```

Run any script with `--help` to see its own options.
