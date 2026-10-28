# Plugin: weather — current conditions and a two-day outlook

**Kind:** skill (knowledge the think loop executes with tools it
already has: `run_shell`). No secret, no vault service, no new
infrastructure.

**What it does:** answers "look up the weather" with a *measured*
report from [wttr.in](https://wttr.in) (a public weather service
fronting WorldWeatherOnline data; no API key). Current conditions
plus today/tomorrow high-low for a named place. If no place is
named, use **Sitka, Alaska** — the owner's home port.

**Why it exists:** the voice once invented a Sitka forecast
(52°F, light rain) that existed nowhere in the record. This
plugin is the mechanical route to a real one: the numbers in a
weather report come from this recipe's output, never from the
model. (The work-through transfers the script, not the
measurement.)

## The recipe

Place name below is `PLACE` (e.g. `Sitka`, `Juneau, Alaska`).

1. Fetch (JSON, one call):

   ```bash
   curl -s --max-time 25 "https://wttr.in/$(printf %s "$PLACE" | sed 's/ /%20/g')?format=j1" -o /tmp/wx.json
   ```

2. Check the fetch worked before reading anything from it:

   ```bash
   jq -e '.current_condition[0]' /tmp/wx.json >/dev/null
   ```

   Non-zero exit, an empty file, or a missing field means the
   lookup FAILED — go to Failure, below.

3. Read the numbers (exactly these fields):

   ```bash
   jq -r '.current_condition[0] | "Now: \(.weatherDesc[0].value | gsub("^ +| +$"; "" )), \(.temp_F)F (\(.temp_C)C), feels \(.FeelsLikeF)F; wind \(.winddir16Point) \(.windspeedMiles) mph; humidity \(.humidity)%; precip \(.precipInches) in; observed \(.observation_time)"' /tmp/wx.json
   jq -r '.weather[0] | "Today: high \(.maxtempF)F, low \(.mintempF)F"' /tmp/wx.json
   jq -r '.weather[1] | "Tomorrow: high \(.maxtempF)F, low \(.mintempF)F, midday: \(.hourly[4].weatherDesc[0].value | gsub("^ +| +$"; "" ))"' /tmp/wx.json
   ```

   If `jq` is somehow missing, the same three reads in python3:
   `current_condition[0]` (`temp_F`, `temp_C`, `FeelsLikeF`,
   `weatherDesc[0].value`, `winddir16Point`, `windspeedMiles`,
   `humidity`, `precipInches`, `observation_time`),
   `weather[0]`/`weather[1]` (`maxtempF`, `mintempF`,
   `hourly[4].weatherDesc[0].value`).

## The report

When this answers a board task, file a **written report**
(reports/README.md) whose body is 1–3 plain sentences built ONLY
from the recipe's output, in this shape (numbers are a format
example, not data):

> Sitka weather from wttr.in (observed 03:23 AM): clear, 39°F
> (4°C), feels like 33°F; wind NNE 6 mph; humidity 61%; no
> precip. Today high 45°F, low 36°F. Tomorrow high 44°F, low
> 37°F, midday overcast.

Name the place and the source. Quote the observation time
exactly as the payload gives it. Do not round beyond what the
fields carry, do not add advice the data doesn't support, and
do not convert units the fields already provide.

## Failure

If the fetch or the check fails, the report says so, with the
actual error (curl's exit, the empty response, the missing
field) — for example: "Weather lookup for Sitka failed: wttr.in
returned no current conditions. No estimate — the service did
not answer." A failed lookup still closes the task it answered:
the lookup was the work, and the failure is the honest outcome.
**Never** fill a gap in the output with a plausible number. An
invented forecast is the one result worse than no result.

## Provenance

Authored in the lab (SuperInstance/xero-lab, `plugins/weather/`)
and grabbed into this repo under the grabber contract
(plugins/README.md). Improvements land on the shelf first, then
are re-grabbed; never edit a grabbed copy and call it the shelf
version.
