"""Per-day tallies: messages, and uses of a given word.

One aggregator, `per_day`, backs both, because a message is just a word count of 1 per row.
"""
from __future__ import annotations

import re

import pandas as pd

from .loading import resolve_users
from .periods import period_grouper, period_start, resample_counts


def selected(df: pd.DataFrame, users: list[str]) -> pd.DataFrame:
    """The chosen users' messages in time order, with a canonical `User` column."""
    lower = {u.lower(): u for u in users}
    sub = df[df["Username"].str.lower().isin(lower)].copy()
    sub["User"] = sub["Username"].str.lower().map(lower)
    return sub.sort_values("Timestamp").reset_index(drop=True)


def period_stats(
    frame: pd.DataFrame,
    users: list[str],
    column: str,
    period: str = "W",
    min_rows: int = 1,
    index_from: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Mean, median and quartiles of `column` per period per user.

    `frame` must already carry the `User` and `Date` columns that `selected` adds.
    Periods holding fewer than `min_rows` rows come back blank, so one stray value
    cannot masquerade as a trend. `index_from` supplies the date range when `frame`
    has been filtered down to a subset of the messages.
    """
    g = frame.groupby([period_grouper(period), "User"])[column]
    span = index_from if index_from is not None else frame
    full = resample_counts(pd.DataFrame(index=pd.date_range(span["Date"].min(), span["Date"].max()),
                                        columns=users, data=0), period).index
    enough = g.size().unstack().reindex(index=full, columns=users) >= min_rows
    out = {name: fn.unstack().reindex(index=full, columns=users).where(enough)
           for name, fn in {"mean": g.mean(), "median": g.median(),
                            "q25": g.quantile(0.25), "q75": g.quantile(0.75)}.items()}
    out["n"] = g.size().unstack().reindex(index=full, columns=users).fillna(0).astype(int)
    return out


def windowed_stats(
    frame: pd.DataFrame,
    users: list[str],
    column: str,
    period: str = "W",
    window: int = 1,
    min_rows: int = 1,
    index_from: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """period_stats, taken over the trailing `window` periods instead of one.

    A median cannot be smoothed by averaging the weekly medians, so each point is
    worked out afresh from every row in its window. A window of one is period_stats.
    """
    if window <= 1:
        return period_stats(frame, users, column, period, min_rows, index_from)
    index = period_stats(frame, users, column, period, 1, index_from)["n"].index
    starts = period_start(frame["Date"], period)
    out = {name: pd.DataFrame(index=index, columns=users, dtype=float)
           for name in ("mean", "median", "q25", "q75")}
    out["n"] = pd.DataFrame(0, index=index, columns=users)
    for i, end in enumerate(index):
        rows = frame[(starts >= index[max(0, i - window + 1)]) & (starts <= end)]
        for u in users:
            x = rows.loc[rows["User"] == u, column]
            out["n"].loc[end, u] = len(x)
            if len(x) >= max(min_rows, 1):
                out["mean"].loc[end, u], out["median"].loc[end, u] = x.mean(), x.median()
                out["q25"].loc[end, u], out["q75"].loc[end, u] = x.quantile(0.25), x.quantile(0.75)
    return out


def per_day(df: pd.DataFrame, users: list[str], values: pd.Series | None = None) -> pd.DataFrame:
    """Sum `values` (default: 1 per message) per day per user, zero-filling gaps."""
    lower = {u.lower(): u for u in users}
    mask = df["Username"].str.lower().isin(lower)
    sub = pd.DataFrame({
        "Date": df.loc[mask, "Date"],
        "User": df.loc[mask, "Username"].str.lower().map(lower),
        "Value": 1 if values is None else values[mask],
    })
    counts = sub.groupby(["Date", "User"])["Value"].sum().unstack(fill_value=0)
    full_range = pd.date_range(df["Date"].min(), df["Date"].max(), freq="D")
    counts = counts.reindex(full_range, fill_value=0).reindex(columns=users, fill_value=0)
    counts.index.name = "Date"
    return counts.astype(int)


def daily_counts(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Messages per day per user, with zero-filled gaps across the full range."""
    users = resolve_users(df, users)
    return per_day(df, users)


def daily_words(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Words written per day per user, with zero-filled gaps across the full range."""
    users = resolve_users(df, users)
    return per_day(df, users, df["WordCount"])


URL = re.compile(r"https?://\S+", re.IGNORECASE)


# How a question is worded when it carries no question mark. Each pattern is matched
# against the message in lower case with apostrophes removed, so "what's" is "whats".
# They are deliberately narrow: "how" must be followed by a verb or a measure, or
# "how lovely" would count, and "which" and "where" must not be starting a clause.
_LEAD = r"^(?:(?:so|and|but|or|wait|oh|btw|also|ok|okay|well|then|hmm+) )?"
_SUBJECT = (r"(?:you|u|ya|we|i|he|she|it|they|that|this|these|those|there|anyone|everyone|"
            r"your|ur|the)")
_VERB = r"(?:is|are|was|were|am|do|does|did|can|could|should|would|will|shall|have|has)"
QUESTION_WORDING = re.compile("|".join([
    # what / who / why, and their contractions
    _LEAD + r"(?:what(?! a\b)|whats|whatre|who|whos|whose|why|whys)\b",
    # where / when / which, only when a verb or the person follows
    _LEAD + rf"(?:wheres|whereabouts|whens|(?:where|when) (?:{_VERB}|u|you|to)\b)",
    _LEAD + r"which (?:one|ones|(?:\w+ )?(?:do|does|did|would|should|shall|can|could) "
            r"(?:you|u|ya|we|i))\b",
    # how, followed by a verb or a measure
    _LEAD + rf"(?:hows|howd|how (?:{_VERB}|come|about|much|many|long|far|often|old|big|late|"
            r"early|soon|u|ya|you)\b)",
    # verb before subject: "do you", "is it", "can we", "havent they". Not "do it" or
    # "do that", which are instructions.
    _LEAD + rf"(?!do (?:it|that|this|these|those|the)\b)"
            rf"(?:{_VERB}|arent|isnt|wasnt|werent|dont|doesnt|didnt|cant|couldnt|wouldnt|wont|"
            rf"shouldnt|havent|hasnt) {_SUBJECT}\b",
    # asking what the other person wants or thinks
    _LEAD + r"(?:you|u|ya) (?:wanna|want to|want me to|fancy|reckon|think so|sure|free|coming|"
            r"up for)\b",
    _LEAD + r"(?:shall we|should we|should i|mind if|fancy|"
            r"any (?:idea|ideas|plans|luck|chance|news|thoughts)|"
            r"wanna (?:play|call|vc|come|go|join|watch|hop|do|meet|try))\b",
    # a tag on the end: "... is it", "... dont you", "... or"
    r" (?:is it|isnt it|innit|do you|did you|are you|have you|would you|can you|will you|"
    r"dont you|didnt you|arent you|wont you|or+|or what)$",
    r"(?<!uh) huh$",
    # "... right", unless "right" is doing its ordinary job: "get it right", "thats right"
    r"^(?!.*\b(?:it|its|thats|that|get|gets|got|getting|be|is|are|was|done|do|doing|eating|"
    r"them|this|something|quite|just|all|about|not|so|too|very) right$).+ right$",
]))


def is_question(df: pd.DataFrame) -> pd.Series:
    """True for each message that asks something.

    A message counts if it holds a question mark or is worded as a question. The
    wording matters as much as the mark: plenty of questions are typed without one,
    and one user can leave it off far more than the other. Links are removed first,
    because a URL very often carries a question mark of its own.
    """
    text = (df["Content"].str.replace(URL, " ", regex=True).str.lower()
            .str.replace("[’']", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip())
    return text.str.contains("?", regex=False) | text.str.contains(QUESTION_WORDING)


def daily_questions(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Questions asked per day per user."""
    users = resolve_users(df, users)
    return per_day(df, users, is_question(df).astype(int))


def daily_reactions(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Reactions received per day per user: the reactions left on that user's messages."""
    users = resolve_users(df, users)
    return per_day(df, users, df["NReactions"])


def daily_links(df: pd.DataFrame, users: list[str] | None = None) -> pd.DataFrame:
    """Links sent per day per user, counting every URL in a message."""
    users = resolve_users(df, users)
    return per_day(df, users, df["Content"].str.count(URL))


def word_table(sub: pd.DataFrame, by: pd.Series) -> pd.DataFrame:
    """How many messages each word was said in, with one column per value of `by`.

    A word counts once per message however often it is repeated there, so a single
    long list cannot make a word look common. Links are ignored, and apostrophes are
    dropped so that "it's" and "its" count as one word; otherwise a habit of
    punctuation would look like a choice of words.
    """
    text = sub["Content"].str.replace(URL, " ", regex=True).str.lower().str.replace("'", "")
    return (text.str.findall(r"[a-z]{3,}").map(set).explode().dropna()
            .groupby(by).value_counts().unstack(0, fill_value=0))


def distinctive(
    table: pd.DataFrame, n: int = 3, min_uses: int = 25, min_ratio: float = 0.0
) -> dict:
    """The words that set each column of a word table apart from the other columns.

    A word's score is how many times more often it is said in that column than in
    the rest put together. Returns {column: scores}, best first, keeping at most `n`
    words said at least `min_uses` times and scoring at least `min_ratio`.
    """
    rate = table / table.sum()
    out = {}
    for col in table.columns:
        rest = table.drop(columns=col)
        # The +3 stops a word the others never used from scoring infinitely.
        score = rate[col] / ((rest.sum(axis=1) + 3) / max(rest.to_numpy().sum(), 1))
        score = score[(table[col] >= min_uses) & (score >= min_ratio)]
        out[col] = score.sort_values(ascending=False, kind="stable").head(n)
    return out


def signature_words(
    df: pd.DataFrame, users: list[str] | None = None, n: int = 3, min_uses: int = 25
) -> dict[str, list[str]]:
    """Each user's most distinctive words: common for them, rare for everyone else."""
    users = resolve_users(df, users)
    sub = selected(df, users)
    table = word_table(sub, sub["User"]).reindex(columns=users, fill_value=0)
    return {u: list(scores.index) for u, scores in distinctive(table, n, min_uses).items()}


def period_words(
    df: pd.DataFrame, users: list[str] | None = None, period: str = "M", n: int = 8,
    min_uses: int = 8, min_ratio: float = 3.0,
) -> dict[pd.Timestamp, pd.Series]:
    """Each period's most distinctive words, both users together, keyed by its start.

    `min_ratio` is what keeps the filler out: in a quiet period nothing stands out,
    and the best of a bad lot would otherwise be words like "there" and "something".
    """
    users = resolve_users(df, users)
    sub = selected(df, users)
    table = word_table(sub, period_start(sub["Date"], period))
    return distinctive(table, n, min_uses, min_ratio)


def word_pattern(word: str, partial: bool = False) -> re.Pattern:
    """Case-insensitive pattern for a word or phrase.

    Whole-word by default, so "love" matches "love" and "Love!" but not "lovely".
    With partial=True it matches anywhere ("love" also hits "lovely", "gloves").
    A word ending in * matches anything that begins with it ("draw*" hits "drawing").
    A word ending in + lets its last letter repeat ("hai+" hits "haiii" but not "hair").
    Several words joined by | count as one ("mum|mom|mother"), each following the
    rules above in its own right.
    """
    if "|" in word:
        parts = [part.strip() for part in word.split("|") if part.strip()]
        return re.compile("|".join(word_pattern(part, partial).pattern for part in parts),
                          re.IGNORECASE)
    stem = word.rstrip("*+")
    body = r"\s+".join(re.escape(part) for part in stem.split())  # phrases tolerate any spacing
    if partial:
        return re.compile(body, re.IGNORECASE)
    if word.endswith("*"):
        end = r"\w*"  # the end of the word is left open
    elif word.endswith("+") and stem:
        end = re.escape(stem[-1]) + r"*(?!\w)"  # the last letter, as many times as typed
    else:
        end = r"(?!\w)"
    return re.compile(rf"(?<!\w){body}{end}", re.IGNORECASE)


def word_hits(df: pd.DataFrame, word: str, mode: str = "count", partial: bool = False) -> pd.Series:
    """Per-message value for a word: occurrences ("count") or 0/1 ("messages")."""
    hits = df["Content"].str.count(word_pattern(word, partial))
    return (hits > 0).astype(int) if mode == "messages" else hits


def daily_word_counts(
    df: pd.DataFrame,
    word: str,
    users: list[str] | None = None,
    mode: str = "count",
    partial: bool = False,
) -> pd.DataFrame:
    """Uses of `word` per day per user.

    mode="count"    -> total occurrences ("love love love" counts as 3)
    mode="messages" -> number of messages containing the word at least once
    """
    users = resolve_users(df, users)
    return per_day(df, users, word_hits(df, word, mode, partial))


def word_usage_table(
    df: pd.DataFrame,
    words: list[str],
    users: list[str] | None = None,
    partial: bool = False,
) -> pd.DataFrame:
    """Totals per word per user, plus uses per 1,000 messages so users are comparable."""
    users = resolve_users(df, users)
    lower = {u.lower(): u for u in users}
    mask = df["Username"].str.lower().isin(lower)
    who = df.loc[mask, "Username"].str.lower().map(lower)
    msgs = who.value_counts().reindex(users, fill_value=0)

    rows = []
    for w in words:
        uses = word_hits(df[mask], w, "count", partial).groupby(who).sum().reindex(users, fill_value=0)
        for u in users:
            rows.append({
                "Word": w, "User": u, "Uses": int(uses[u]),
                "Per1kMsgs": round(uses[u] / msgs[u] * 1000, 1) if msgs[u] else 0.0,
            })
    return pd.DataFrame(rows).set_index(["Word", "User"])
