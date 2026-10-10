# Discord chat stats

Charts and summaries built from a Discord conversation export between two people.
Every output has its own script, and the code they share lives in the `chatstats`
package.

## Requirements

Python 3.12 or newer, with `pandas` and `matplotlib`.

```
uv sync          # or: pip install pandas matplotlib
```

## The data

The scripts read export pages named `megamoleys-page-NN.csv`. There are 79 of them in
`data/`. Pages are sorted by number, concatenated and deduplicated on message ID, so
overlapping page boundaries do no harm.

The default for `--dir` is the current folder, so in this project you almost always
want `--dir data`.

Two properties of the export are worth knowing, because the scripts work around both
of them.

The `Timestamp` column holds local wall clock time truncated to the minute. That is far
too coarse for reply times, because more than half of all replies land in the same
minute as the message they answer and would therefore read as exactly zero seconds. The
scripts ignore that column and decode the real send time from the message ID instead.
The top 42 bits of a Discord snowflake count milliseconds since 1 January 2015, which
gives millisecond precision in true UTC. The column is used only as a fallback for rows
whose ID cannot be read.

Those wall clock times are also written in Europe/London rather than in UTC. Day and
hour buckets therefore use `--tz`, which defaults to Europe/London, so that a message
sent late at night lands on the night it belongs to.

## Running everything

In PowerShell:

```powershell
$all = 'overview','highlights','calendar_heatmap','messages_per_day','message_length','volume_breakdown','conversation_duration','daily_rhythm','reply_times','initiators','last_word','messages_in_a_row','response_curve','nudges','questions','links','reactions','topics','distinctive_words'
foreach ($s in $all) { python "$s.py" --dir data }
```

In bash:

```bash
for s in overview highlights calendar_heatmap messages_per_day message_length volume_breakdown conversation_duration daily_rhythm \
         reply_times initiators last_word messages_in_a_row response_curve nudges questions links reactions topics distinctive_words; do
    python "$s.py" --dir data
done
```

## Shared arguments

These five are accepted by every script, and they are repeated in each table below for
convenience.

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages inside that folder. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. Matching ignores case. |
| `--tz TZ` | `Europe/London` | The timezone the export's wall clock times were written in. It decides which local day and hour each message counts towards. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |

## Relationship dividers

`--relationship-dividers` works on every script. It marks two dates on the chart: the
day we got together, 30 November 2025, and the day we broke up, 19 September 2026.

On a chart with a date axis each is a black vertical line through every panel,
labelled at the foot of the top one. Three charts have no date axis and mark the dates their own
way. `daily_rhythm.py` draws the lines between its month columns, placed by how far
through the month the date falls. `distinctive_words.py` runs time down the page, so
its lines lie across, each between the two rows nearest its date. `calendar_heatmap.py` outlines the two days and names them in
the note under its title. `response_curve.py`, `highlights.py` and `overview.py` have nothing to mark
and accept the option without effect.

The dates and labels are `RELATIONSHIP_DIVIDERS` at the top of `chatstats/plotting.py`.

```
python initiators.py --dir data --relationship-dividers
```

## Output

Every chart is written to the `out` folder, which is created if it does not exist.
Each script's `--out` option changes where its chart goes.

## Titles

Every chart carries a short title that names what is plotted and nothing else, such
as "Nudges per Week" or "Reply Time per Week". Anything needed to read the chart, such
as what counts as a conversation or what a band covers, goes in a line of small grey
type under the title. Both are drawn by `chart_title` in `chatstats/plotting.py`.

## Colours

Each user keeps one colour in every chart, so that a line, a shaded span and a bar for
the same person always agree. The colour follows the username rather than its position,
so it does not change when `--users` lists them the other way round.

| User | Colour |
| --- | --- |
| `megamoleys` | Navy leaning purple, `#3B2E8F` |
| `triflicacid` | Orange, `#E8730C` |

Any username not listed above takes the next spare colour. Red is kept out of the spare
set so that nothing competes with the crimson total line on `messages_per_day.py`. To
change a colour, or to pin one for another user, edit `USER_COLORS` at the top of
`chatstats/plotting.py`.

Quantities belonging to the pair rather than to one person use their own colours, so
that they are never mistaken for a user. The combined total is crimson, conversations
are a dark slate, and the heatmaps on `daily_rhythm.py` use a single teal ramp running
light to dark. Teal deliberately: orange and navy already mean a specific person
everywhere else.

## overview.py

Prints a text summary and writes no chart.

It reports the total message count, the date range and the number of authors. It then
prints a table for each user covering messages sent, words written, messages carrying
an attachment, total attachments, total reactions, active days, share of all messages,
average words per message and messages per active day. After that it prints each user's
daily mean and median, their busiest day, how many days they were silent, a breakdown
by weekday, and the busiest hour of the day.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--csv CSV` | not saved | Also writes the per user table to this CSV file. |

### Examples

```
python overview.py --dir data
python overview.py --dir data --csv per_user.csv
python overview.py --dir data --tz UTC
```

## highlights.py

Writes `out/highlights.png`, a card of headline numbers with no axes at all.

The upper part holds the numbers that belong to both of us: total messages and words,
how many days had at least one message, the longest streak of days in a row, the
longest silence, the busiest day, how many conversations there were and the size of a
typical one, the biggest single conversation, the fastest 100 messages, the busiest
hour and weekday, and the links and attachments shared.

The lower part gives each user the same ten numbers in their own colour, side by side:
messages, words, conversations started, days sending the first message, the typical
time to reply, how often they spoke again after an hour unanswered, questions asked,
links and attachments sent, their longest message, and their three signature words. A
signature word is one that user
says often and the other hardly ever, ranked by how many times more often they say it.
Links are ignored and apostrophes are dropped first, so that "it's" and "its" count as
one word and a habit of punctuation does not take every place.

Every number on the card is also printed to the terminal.

`--output-longest` also writes each user's longest messages in full to a text file
named after them, such as `triflicacid.txt` and `megamoleys.txt`, in the current
folder. Each message is headed by its rank, date, time and word count, longest first.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to include. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. It only affects the biggest conversation tile. |
| `--out OUT` | `out/highlights.png` | Where to write the card. |
| `--output-longest [N]` | off | Also writes each user's N longest messages to `<username>.txt`. N is 10 when the flag is given without a number. |

### Examples

```
python highlights.py --dir data
python highlights.py --dir data --gap 4
python highlights.py --dir data --output-longest
python highlights.py --dir data --output-longest 25
python highlights.py --dir data --out highlights.svg
```

## calendar_heatmap.py

Writes `out/calendar_heatmap.png`.

Draws every day in the range as one square, coloured by how many messages were sent
on it. Weeks run left to right and weekdays top to bottom, so a streak shows as a
solid block and a silence as a gap. Both users are counted together.

The colour scale is logarithmic. The busiest day holds over a thousand messages and a
typical one a few dozen, so on a linear scale every ordinary day would be the same
pale square. A day on which nobody said anything is grey, which keeps it apart from
the white of days outside the range.

A ring marks the busiest day, and a line under the grid marks the longest streak of
days in a row with at least one message. The three longest streaks are printed to the
terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to count. They are pooled rather than compared. |
| `--tz TZ` | `Europe/London` | The timezone that decides which day a message belongs to. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/calendar_heatmap.png` | Where to write the chart. |

### Examples

```
python calendar_heatmap.py --dir data
python calendar_heatmap.py --dir data --tz UTC
python calendar_heatmap.py --dir data --out calendar.svg
```

## messages_per_day.py

Writes `out/messages_per_day.png`, a chart of three panels sharing one date axis.

**The main panel** draws one line per user showing how many messages they sent each
day, plus a red line for the combined total of both users.

Its y axis uses a symmetrical log scale by default. A typical day carries around 26
messages per user while the busiest carries more than 900, so a linear axis squeezes
most of the year into the bottom of the chart. A symmetrical log scale is linear below
1, which means days with no messages at all still appear at zero rather than vanishing
the way they would on an ordinary log scale.

Each user's busiest days are marked with a dot and labelled with the count and the
date. Stretches where both users were quiet are shaded grey. Stretches where only one
of them was quiet are shaded in that user's own colour, except where a solo gap falls
entirely inside a shared silence, since the grey shading already covers it. The same
peaks and silences are printed to the terminal.

**The middle panel** is the running total for each user and for the pair together. It
is deliberately short, because it is there for the overall shape rather than for
reading values off, and it is always linear whatever `--axis` is set to. Slope is the
rate, so a flat stretch is a silence and a bend is a lasting change of pace.

**The lower panel** is each user's share of that period's messages, as a stacked area
out of 100%, with a dashed line at 50%. Periods in which neither of them said anything
are left blank rather than drawn as an even split between nobody.

Counting words rather than messages, with `--metric words`, changes all three panels
together, so they become words per day, cumulative words and share of words.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/messages_per_day.png` | Where to write the chart. Any extension matplotlib supports will work, such as `.png`, `.svg` or `.pdf`. |
| `--metric {messages,words}` | `messages` | What to count. The messages setting counts one per message. The words setting counts the words inside them instead, which rescales all three panels together. |
| `--period {D,W,M}` | `D` | Whether to count messages by day, by week starting on Monday, or by calendar month. |
| `--rolling ROLLING` | `0` | Draws a rolling average over this many periods on top of a faint copy of the raw line. Zero leaves the line unsmoothed. |
| `--axis {linear,log}` | `log` | The y axis scale. The log setting is a symmetrical log scale, so silent days still plot at zero. The linear setting gives the plain view. `--yscale` is accepted as an older spelling of the same option. |
| `--total {true,false}` | `true` | Whether to draw the red line for both users combined. Setting it to false leaves only the individual lines, which also lowers the top of the axis. |
| `--peaks PEAKS` | `5` | How many of each user's busiest periods to mark and label. Zero turns the labels off. |
| `--peak-distance PEAK_DISTANCE` | 14 days, 4 weeks or 2 months | The minimum number of periods between two labelled peaks, which stops a single busy week producing a cluster of labels. |
| `--quiet QUIET` | `12` | How many of the longest stretches where both users were quiet to shade in grey. Zero turns the shading off. |
| `--quiet-min QUIET_MIN` | `1` | Ignores any shared quiet stretch shorter than this many periods. |
| `--user-quiet USER_QUIET` | `6` | How many of each user's own longest quiet stretches to shade in their colour. Zero turns the shading off. |
| `--user-quiet-min USER_QUIET_MIN` | 2 days, 1 week or 1 month | Ignores any solo gap shorter than this many periods. |
| `--quiet-threshold QUIET_THRESHOLD` | `5` | A period counts as quiet when its count is at or below this number. Zero means completely silent. It applies to the combined total for `--quiet` and to each user's own count for `--user-quiet`. |
| `--csv CSV` | not saved | Also writes the table of daily counts to this CSV file, following whichever `--metric` is in use. |

### Examples

```
python messages_per_day.py --dir data
python messages_per_day.py --dir data --period W --rolling 4
python messages_per_day.py --dir data --axis linear
python messages_per_day.py --dir data --total false
python messages_per_day.py --dir data --metric words
python messages_per_day.py --dir data --metric words --period W
python messages_per_day.py --dir data --peaks 8 --quiet 5
python messages_per_day.py --dir data --peaks 0 --quiet 0 --user-quiet 0
python messages_per_day.py --dir data --quiet-threshold 0 --quiet 3 --user-quiet 3
python messages_per_day.py --dir data --user-quiet 5 --user-quiet-min 7
python messages_per_day.py --dir data --csv daily.csv --out chart.svg
```

## message_length.py

Writes `out/message_length.png`.

Counting messages tells you how much someone talked. This tells you how they talked.
It draws the mean number of words per message, one point per week, for each user, with
the middle 50% of individual messages shaded behind each line.

The line is the mean because that is what average message length normally means, and
it matches the figure `overview.py` reports. The band is a quartile range rather than
anything derived from the mean, which keeps the skew visible: most messages are very
short, and a handful of long ones pull the mean above the median. Periods holding
fewer messages than `--min-messages` are left blank.

The two measures move independently. In this export they move in opposite directions,
with both users sagging to roughly 4 words per message through the busiest part of
spring and climbing to 6 or more through the quiet summer.

`--text-only` matters more than it sounds. Messages with no words at all are usually an
image or a link on its own, and the two users send very different numbers of them, so
leaving them in flatters whoever sends more. Here it moves the comparison from 5.69
against 5.20 words to 5.97 against 5.28.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/message_length.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--min-messages MIN_MESSAGES` | `10` | Leaves a period blank when it holds fewer messages than this, so that a quiet week cannot produce a spike. |
| `--text-only` | off | Ignores messages that contain no words at all, which are usually an image or a link on its own. |

### Examples

```
python message_length.py --dir data
python message_length.py --dir data --text-only
python message_length.py --dir data --period M
python message_length.py --dir data --min-messages 50
python message_length.py --dir data --out length.svg
```

## volume_breakdown.py

Writes `out/volume_breakdown.png`.

Words written is conversations held, times messages sent in each, times words in each
message. This chart puts the four on one date axis so that a change in how much was
said can be attributed instead of guessed at: talking less often, shorter
conversations, or shorter messages.

The top panel is words per week, one line per user. Under it are the three factors.
Conversations per week has a single line, because a conversation belongs to both of
us. Messages per conversation and words per message have one line per user. The three
lower panels multiply back to the top one.

In this export the number of conversations barely moved across the year while their
size collapsed, so the fall in volume was conversations getting shorter and not rarer.
Words per message moved the other way, dipping in spring and recovering over the
summer. The printed summary gives the two halves of the date range side by side.

Every panel is a 4 week average over a faint copy of the raw line. Each ratio is
smoothed as one window total over another, which is its true average and keeps the
panels multiplying back. Words per message is left blank where it would rest on fewer
than `--min-messages`.

`messages_per_day.py` has the daily counts, peaks and silences, and
`message_length.py` has the spread of individual messages.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. Raising it gives fewer and larger conversations, which moves the two middle panels. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--out OUT` | `out/volume_breakdown.png` | Where to write the chart. |
| `--min-messages MIN_MESSAGES` | `10` | Leaves words per message blank where it would rest on fewer messages than this. |
| `--rolling ROLLING` | `4` | Smooths every panel over this many periods. Zero leaves them raw. |

### Examples

```
python volume_breakdown.py --dir data
python volume_breakdown.py --dir data --gap 4
python volume_breakdown.py --dir data --rolling 0
python volume_breakdown.py --dir data --period M --rolling 0
python volume_breakdown.py --dir data --out breakdown.svg
```

## conversation_duration.py

Writes `out/conversation_duration.png`.

Shows how long conversations last in time, which `volume_breakdown.py` does not: that
chart measures a conversation in messages. Duration is the time from the first message
of a conversation to its last.

The upper row has one chart per user, side by side, for the conversations that user
started. The line is the median duration and the band is the middle half of
conversations. The axis is logarithmic, because durations run from a minute to most of
a day. The lower panel is the difference between the two medians in minutes, filled in
the colour of whichever user's conversations lasted longer. It needs exactly two users
and is left out otherwise.

Only conversations both users took part in are counted. One that nobody answered has
no duration worth the name, and in this export that is about a third of them. The
printed summary says how many were left out.

A median cannot be smoothed by averaging weekly medians, so each point is worked out
afresh from every conversation in the previous 4 weeks. Points resting on fewer than
`--min-conversations` are left blank.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare, one chart each. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. Raising it joins conversations together and makes them longer. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--out OUT` | `out/conversation_duration.png` | Where to write the chart. |
| `--min-conversations MIN_CONVERSATIONS` | `5` | Leaves a point blank where it would rest on fewer conversations than this. |
| `--rolling ROLLING` | `4` | How many periods each point looks back over. Zero or one uses the period alone. |

### Examples

```
python conversation_duration.py --dir data
python conversation_duration.py --dir data --gap 4
python conversation_duration.py --dir data --min-conversations 8
python conversation_duration.py --dir data --period M --rolling 0
```

## reply_times.py

Writes `out/reply_times.png`.

Draws the median time each user takes to reply, one point per week, on a logarithmic y
axis. A shaded band behind each line covers the middle 50 percent of that week's
replies, running from the lower quartile to the upper quartile. Weeks holding fewer
replies than `--min-replies` are left blank, so that a single slow reply cannot create
a spike.

This chart counts only replies made inside a conversation. Any silence longer than
`--gap` is treated as the start of a new conversation rather than as a slow reply, so
every long wait is excluded by design. To see those waits instead, use
`response_curve.py`.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. Replies slower than this are counted as a new conversation and leave the chart entirely. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--out OUT` | `out/reply_times.png` | Where to write the chart. |
| `--min-replies MIN_REPLIES` | `3` | Leaves a period blank when it holds fewer replies than this. |

### Examples

```
python reply_times.py --dir data
python reply_times.py --dir data --gap 3
python reply_times.py --dir data --period M
python reply_times.py --dir data --min-replies 10
python reply_times.py --dir data --out replies.svg
```

## initiators.py

Writes `out/initiators.png`.

Draws three panels that share one date axis.

The top panel shows how many conversations each user started in each week, with their
running total and their overall share given in the legend.

The middle panel shows each user's share of the starts over time as a stacked area,
with a dashed line at 50 percent so you can read at a glance who was above or below
parity in any given week. Weeks in which nothing happened are left empty rather than
drawn as an even split.

The bottom panel is the same kind of share, for who sent the first message of the day.
It needs no definition of a conversation, so it does not move with `--gap`. The day
turns over at `--day-start` rather than at midnight, so a message at 1am carries on the
night before instead of opening the next day.

Weekly starts are small numbers, so this chart is smoothed by default. The top panel
draws a 4 week average over a faint copy of the raw line, and both share panels are
taken over the same 4 weeks. `--rolling 0` gives the raw weekly view.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. This decides what counts as starting one, so raising it produces fewer and longer conversations. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--out OUT` | `out/initiators.png` | Where to write the chart. |
| `--day-start DAY_START` | `5` | The local hour at which a new day begins for the first message panel. |
| `--rolling ROLLING` | `4` | Smooths the top panel over this many periods and takes both shares over the same window. Zero leaves everything raw. |

### Examples

```
python initiators.py --dir data
python initiators.py --dir data --gap 4
python initiators.py --dir data --rolling 0
python initiators.py --dir data --day-start 4
python initiators.py --dir data --period M --rolling 0
python initiators.py --dir data --out starts.png
```

## last_word.py

Writes `out/last_word.png`.

The counterpart to `initiators.py`: who sent the final message of each conversation,
the one followed by `--gap` hours of silence. The upper panel is conversations ended
per week by each user, as a 4 week average over a faint copy of the raw line. The
lower panel is each user's share of them over the same 4 weeks.

Having the last word here means being the one left without an answer, so a rising
share is not a sign of winning anything. A conversation nobody answered at all is
ended by the person who started it, which ties this chart to the one above: whoever
starts more conversations that go unanswered also ends more.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. This decides what counts as the last word. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--out OUT` | `out/last_word.png` | Where to write the chart. |
| `--rolling ROLLING` | `4` | Smooths the upper panel over this many periods and takes the share over the same window. Zero leaves both raw. |

### Examples

```
python last_word.py --dir data
python last_word.py --dir data --gap 4
python last_word.py --dir data --period M --rolling 0
```

## messages_in_a_row.py

Writes `out/messages_in_a_row.png`.

Draws how many messages each user sends in a row before the other one replies, as an
average per week. A run of messages by one person is a turn, and this is the mean
length of a turn. A value of 1 means strict back and forth, and a rising line means
that user is saying more and more before getting an answer.

The line is a 4 week average over a faint copy of the raw one. It is worked out as the
window's messages over the window's turns, which is its true average, and is left
blank where that would rest on fewer than `--min-turns`.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/messages_in_a_row.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to plot one point per day, per week starting on Monday, or per calendar month. |
| `--min-turns MIN_TURNS` | `10` | Leaves the line blank where it would rest on fewer turns than this. |
| `--rolling ROLLING` | `4` | Smooths the line over this many periods. Zero leaves it raw. |

### Examples

```
python messages_in_a_row.py --dir data
python messages_in_a_row.py --dir data --rolling 0
python messages_in_a_row.py --dir data --period M --rolling 0
```

## response_curve.py

Writes `out/response_curve.png`.

Splits every handover at `--gap` and draws the two halves as separate panels, because
on a single axis the common case hides the rare one.

The top panel is a survival curve for replies made inside a conversation. It shows the
share of messages still unanswered after each amount of elapsed time, on a logarithmic
x axis, with one line per responder. The point where each line crosses 50 percent and
the point where it crosses 10 percent are both marked and labelled.

The bottom panel covers the waits that ran past `--gap`, grouped by how long they
lasted: 2h to 3h, 3h to 6h, 6h to 12h, 12h to 24h, and over 24h. The pale bar counts
every wait in a group. The solid bar drawn over it counts the ones where the waiter
nudged, meaning they spoke again after `--nudge-hours` with still no answer.

A footer under both panels repeats every handover from the waiting side: how many times
each user waited, how many of those waits ran over an hour, the median length of those,
and how many nudges they sent.

Unlike `reply_times.py`, this script keeps every handover, including the ones that run
overnight.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--gap GAP` | `2.0` | How many hours of silence end a conversation. It also sets where the two panels divide and where the wait buckets begin. |
| `--out OUT` | `out/response_curve.png` | Where to write the chart. |
| `--nudge-hours NUDGE_HOURS` | `1.0` | How many hours of no answer must pass before speaking again counts as a nudge. |

### Examples

```
python response_curve.py --dir data
python response_curve.py --dir data --gap 4
python response_curve.py --dir data --nudge-hours 2
python response_curve.py --dir data --gap 6 --nudge-hours 3
python response_curve.py --dir data --out waiting.png
```

## nudges.py

Writes `out/nudges.png`.

A nudge is speaking again after `--hours` with still no answer. `response_curve.py`
only totals the nudges, which hides who was sending them when, so this chart puts them
on a date axis. Its upper panel is nudges sent per week by each user, as a 4 week
average over a faint copy of the raw line. Its lower panel is each user's share of the
nudges over the same 4 weeks. Each nudge is dated by the nudge itself rather than by
the start of the wait it belongs to.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/nudges.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--hours HOURS` | `1.0` | How many hours of no answer must pass before speaking again counts as a nudge. |
| `--rolling ROLLING` | `4` | Smooths the upper panel over this many periods and takes the share over the same window. Zero leaves both raw. |

### Examples

```
python nudges.py --dir data
python nudges.py --dir data --hours 2
python nudges.py --dir data --rolling 0
python nudges.py --dir data --period M --rolling 0
```

## questions.py

Writes `out/questions.png`.

Draws how many questions each user asked per week, with each user's share of them in
a panel underneath. A question is a message that holds a question mark or is worded
as a question.

The wording test is what makes the count fair. In this export one user leaves the
question mark off roughly three questions in four, so counting marks alone gave a 70
to 30 split where the real one is close to even. A message counts as worded like a
question when it opens with a question word ("what", "why", "how are", "when do"),
opens with the verb before the subject ("do you", "is it", "can we"), asks what the
other person wants ("you wanna", "shall we", "any plans"), or ends in a tag ("... is
it", "... dont you", "... or", "... right"). The patterns are deliberately narrow, so
"how lovely", "which is nice" and "do it anyway" do not count. They are
`QUESTION_WORDING` in `chatstats/counts.py`. Links are removed before either test,
since a URL often carries a question mark.

It is a rule of thumb and not a reading of the message. In a sample of the questions
found by wording alone, about nine in ten were real questions.

Asking is a way of keeping a conversation going and of showing interest in the other
person, so a user's share falling here means they were prompting less.

The upper panel is a 4 week average over a faint copy of the raw line, and the share
is taken over the same 4 weeks. The totals are printed to the terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/questions.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--rolling ROLLING` | `4` | Smooths the upper panel over this many periods and takes the share over the same window. Zero leaves both raw. |

### Examples

```
python questions.py --dir data
python questions.py --dir data --rolling 0
python questions.py --dir data --period M --rolling 0
python questions.py --dir data --relationship-dividers
```

## links.py

Writes `out/links.png`.

Draws how many links each user shared per week, with each user's share of them in a
panel underneath. Every URL counts, so a message holding two links counts twice.

Sharing a link is a way of starting something, which makes this a measure of who is
bringing things to the conversation rather than of how much they are saying. In this
export one user sent roughly twice as many links as the other until March, and the
balance reversed in June.

A handful of links a week is too few to read raw, so the upper panel is a 4 week
average over a faint copy of the raw line, and the share is taken over the same 4
weeks.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/links.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--rolling ROLLING` | `4` | Smooths the upper panel over this many periods and takes the share over the same window. Zero leaves both raw. |

### Examples

```
python links.py --dir data
python links.py --dir data --rolling 0
python links.py --dir data --period M --rolling 0
python links.py --dir data --out links.svg
```

## reactions.py

Writes `out/reactions.png`.

Draws how many reactions each user's messages received per week, with each user's
share of them in a panel underneath.

The export records how many reactions a message got, but not who gave them. With two
people in the conversation a reaction on one user's message is almost always from the
other one, so each line is best read the other way round: the line for one user shows
the other person reacting to them.

Reactions are rare, so the upper panel is a 4 week average over a faint copy of the
raw line, and the share is taken over the same 4 weeks. The totals are printed to the
terminal.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/reactions.png` | Where to write the chart. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--rolling ROLLING` | `4` | Smooths the upper panel over this many periods and takes the share over the same window. Zero leaves both raw. |

### Examples

```
python reactions.py --dir data
python reactions.py --dir data --rolling 0
python reactions.py --dir data --period M --rolling 0
python reactions.py --dir data --relationship-dividers
```

## topics.py

Writes `out/topics.png`.

Shows what each of us talked about over time, using a list of topics and the words
that belong to each. It draws one chart per user, side by side, with a heatmap
under them showing where the two differ. Nothing here works a topic out for itself. It counts the words the
topic file tells it to count, which keeps it repeatable and free of any outside
service.

**The topic file** is `topics.toml` in the project folder. Each line is a topic name
and its words:

```toml
art = ["art", "artwork", "draw*", "sketch*"]
"seeing each other" = ["meet*", "visit*", "train", "london"]
```

A word matches whole and ignores case, so "art" does not match "start". A word ending
in `*` matches anything that begins with it, and a word ending in `+` lets its last
letter repeat, so `yay+` covers "yaaay" typed with any number of letters at the end. A message counts once for each topic it
mentions, and links are ignored. Edit the file freely; the chart follows it, and the
topics are stacked in the order the file lists them.

**The upper panel** in each column is that user's mix: each topic's share of their
own topic mentions, out of 100%, over a 4 week window. It shows what took the place
of what. Stretches where that user has fewer than `--min-mentions` are left blank.

**The middle panel** compares the two. It is a heatmap with a row for each topic and
a column for each week, and each cell is one user's share of that topic minus the
other's, in percentage points. A cell takes the colour of whoever gave the topic more
of their talk, darker for a bigger gap, and is white where the two match. Weeks in
which either user has too few mentions to compare are grey. A large change in what
one of us was talking about shows as a row changing colour or fading out. The colour
scale stops a little short of the single largest gap, so one unusual week does not
wash out the rest. This panel needs exactly two users and is left out otherwise.

**The lower panel** is a single chart with one line per user: the share of that
user's messages that mention any listed topic, drawn in their colour. It is the
reminder that the list covers only part of what was said.

The two columns share their vertical axes, so a band or a line at the same height
means the same thing on either side. The mix is a share of each user's own mentions, though, so
a wider band on one side means that topic took up more of that person's talk, not that
they mentioned it more times.

The printed summary gives each user's total for each topic and the month it peaked
in.

Use `distinctive_words.py` to find words worth adding.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to chart, one column each. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/topics.png` | Where to write the chart. |
| `--topics TOPICS` | `topics.toml` | The file of topic names and their words. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--min-mentions MIN_MENTIONS` | `10` | Leaves a user's mix blank where it would rest on fewer of their topic mentions than this. |
| `--rolling ROLLING` | `4` | Takes the mix and the coverage over this many periods. Zero leaves both raw. |

### Examples

```
python topics.py --dir data
python topics.py --dir data --period M --rolling 0
python topics.py --dir data --topics my_topics.toml
python topics.py --dir data --rolling 8
```

## distinctive_words.py

Writes `out/distinctive_words.png`.

Lists the words that set each month apart from the rest of the history, with no list
of what to look for. A word appears under a month when it was said at least
`--min-ratio` times more often then than in every other month put together. Each row
is a month, the strongest word comes first, and the colour shows how strong.

A word counts once per message however often it is repeated there, so one long list
cannot put a word on the chart by itself. Links are ignored and apostrophes are
dropped, so "it's" and "its" count as one word. `--min-ratio` is what keeps filler out: in a quiet month nothing stands out, and such
a row is left short or empty instead of being padded with words like "there".

The words are shown exactly as they were typed. The same lists are printed to the
terminal with each word's score.

This is the same calculation as the signature words on the Highlights card, grouped
by month instead of by person.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to count. They are pooled rather than compared. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/distinctive_words.png` | Where to write the chart. |
| `--period {D,W,M}` | `M` | How long each row covers. |
| `--top TOP` | `8` | The most words to list in each row. |
| `--min-uses MIN_USES` | `8` | Ignores a word that appears in fewer messages than this in the period. |
| `--min-ratio MIN_RATIO` | `3.0` | How many times more common than elsewhere a word must be to be listed. |

### Examples

```
python distinctive_words.py --dir data
python distinctive_words.py --dir data --top 12
python distinctive_words.py --dir data --min-ratio 2 --min-uses 5
python distinctive_words.py --dir data --period W
```

## daily_rhythm.py

Writes `out/daily_rhythm.png`.

Two heatmaps showing when in the day and the week the conversation happens, and
whether that changed over the year. The upper one is hour of day, the lower one is day
of week, and both run across the same months.

Every column is normalised to its own month, so the cells are shares rather than
counts. That is the whole point: raw counts would simply restate the volume trend and
bury the rhythm. A ring marks each month's busiest row, which is one direct label per
column rather than a number in all three hundred cells.

Both users are counted together. We are talking to each other, so our clocks are
forced into alignment, and splitting the chart by user produces two almost identical
panels. The largest gap between them in any hour of the day is under one percentage
point.

The printed summary compares the two halves of the date range rather than the first
and last columns, because the range begins and ends mid month and those columns cover
only a few days each.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to count. They are pooled rather than compared. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. This chart is entirely about local time, so it matters more here than anywhere else. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--out OUT` | `out/daily_rhythm.png` | Where to write the chart. |
| `--period {D,W,M}` | `M` | How wide each column is. Months are usually right; weeks give a finer but noisier picture. |

### Examples

```
python daily_rhythm.py --dir data
python daily_rhythm.py --dir data --period W
python daily_rhythm.py --dir data --tz UTC
python daily_rhythm.py --dir data --out rhythm.svg
```

## word_usage.py

Writes `out/word_usage.png`, a single file holding one panel per word.

Each panel draws how often each user said that word or phrase over time, with each
user's total in the panel title. The panels are laid out in a grid of up to three
columns and share one date axis and one legend. Every panel keeps its own y axis, so a
common word does not flatten a rare one.

When more than one word is given, the first panel adds them all together, so it shows
each user's combined use of every word listed. A message is counted once for each word
it contains, in either mode. Buckets are weekly by default, because daily counts are mostly
zero. Matching ignores case and matches whole words only, unless `--partial` is given. A
word ending in `*` matches anything that begins with it, so `draw*` also counts
"drawing". A word ending in `+` lets its last letter repeat, so `hai+` counts "hai",
"haii" and "haiiii" but not "hair". Several words joined by `|` are counted together
in one panel, so `"mum|mom|mother"` is a single line that counts all three. Quote it,
or the shell will read the bar as a pipe.
Phrases match across any amount of whitespace, so "love you" also matches "love  you".

This script produces nothing unless `--words` is given. It also prints a table of
totals for each word and user, together with uses per 1,000 messages so that users who
send very different volumes can still be compared.

### Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--dir DIR` | `.` | The folder that holds the export CSV files. |
| `--pattern PATTERN` | `megamoleys-page-*.csv` | The filename glob used to find export pages. |
| `--users USERS [USERS ...]` | `triflicacid megamoleys` | Which usernames to compare. |
| `--tz TZ` | `Europe/London` | The timezone used for local day and hour buckets. |
| `--relationship-dividers` | off | Marks the day we got together and the day we broke up on the chart. |
| `--words WORDS [WORDS ...]` | empty | The words or phrases to chart, one panel each. Quote anything containing a space. Nothing is produced when this is left empty. |
| `--period {D,W,M}` | `W` | Whether to count by day, by week starting on Monday, or by calendar month. |
| `--mode {count,messages}` | `count` | Whether to count every occurrence, so that "love love love" counts as three, or to count the number of messages containing the word at least once. |
| `--partial` | off | Matches inside longer words as well, so that "love" also matches "lovely" and "gloves". |
| `--rolling ROLLING` | `0` | Draws a rolling average over this many periods on top of a faint copy of the raw line. Zero leaves the line unsmoothed. |
| `--out OUT` | `out/word_usage.png` | Where to write the chart. |
| `--columns COLUMNS` | up to 3 | How many panels to place in each row. |
| `--csv CSV` | not saved | Also writes the counts to this CSV file, with one column per word and user. |

### Examples

```
python word_usage.py --dir data --words dear love
python word_usage.py --dir data --words "love you" --period M
python word_usage.py --dir data --words love --partial
python word_usage.py --dir data --words sorry --mode messages
python word_usage.py --dir data --words love --rolling 4
python word_usage.py --dir data --words "mum|mom|mother" "dad|father"
python word_usage.py --dir data --words dear love sorry "miss you" --columns 2
python word_usage.py --dir data --words dear love --out words.svg --csv words.csv
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
daily_rhythm.py        when in the day and week we talk
reply_times.py         median reply time inside a conversation
initiators.py          who opens the conversation, and the day
last_word.py           who sends the last message of a conversation
messages_in_a_row.py   messages sent before the other one replies
response_curve.py      replying in a conversation against waiting for one
nudges.py              nudges sent over time
questions.py           questions each user asked
links.py               links shared over time
reactions.py           reactions each user's messages received
topics.py              what each of us talked about, from topics.toml
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
