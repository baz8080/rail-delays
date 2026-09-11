# rail-delays

Disruption notices from Irish Rail's realtime service feed, read and published
at **https://baz8080.github.io/rail-delays**. Unofficial, and not affiliated
with Iarnród Éireann.

```
delay_cause/   reads what a notice says went wrong, from the notice's own clause
delay_site/    turns the collected notices into the static site
notes/         the decisions, dated, with the rejected alternatives
```

There is no collector here. [`baz8080/lifts`](https://github.com/baz8080/lifts)
polls the feed every 30 minutes into
[`baz8080/lifts-data`](https://github.com/baz8080/lifts-data), and this
repository reads those logs: one endpoint returns the whole feed in one
response, so a second poller would double the request rate for bytes that are
already on disk.

```bash
uv run python -m delay_site --data-dir ../lifts-data     # build out/site/
uv run python -m unittest discover -s tests -t .
```

The design layer is shared with [uisce](https://github.com/baz8080/uisce),
[esb](https://github.com/baz8080/esb) and
[lifts](https://github.com/baz8080/lifts) through
[statusui](https://github.com/baz8080/statusui), pinned in `uv.lock`.

## What it will not say

- **No totals in minutes.** The feed's figures are re-stated as a notice is
  re-worded and mix one observed train with a forecast over a whole line;
  summing them overstates by 1.26x and measures nothing.
- **No percentage of trains delayed.** There is no published roll of the
  services that ran, so there is nothing to divide by.
- **No decoding.** "An incident on the line" is published as that and no more.

`notes/site.md` and `notes/cause-reading.md` have the numbers behind each.
