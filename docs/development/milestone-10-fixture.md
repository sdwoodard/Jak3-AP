# Milestone 10 disposable acceptance fixture

Generate the two ordinary player YAML files from the canonical default template:

```powershell
python .\tools\generate_milestone_10_fixture.py `
  --output-directory .\dist\milestone-10\Players
```

Enable item plando in the local Archipelago generator and generate both files
together. The runner receives Jetboard at task 10, Blaster at task 11, and the
first Progressive Armor at reward location `743020036`. Five guaranteed
single-copy helper-owned useful items occupy the runner's task 12–16 story
locations, so completing those checks sends no unsupported item to the runner.
Unlike weighted filler, these items are present in every canonical pool. Both
slots otherwise retain every canonical option and the normal 147-location
generated contract.

Start the runner client with `JAK3_AP_M10_TEST_GOAL=task16`. Leave the variable
unset for every ordinary seed; any other value is rejected at startup. The
temporary goal becomes durable only after both task-16 story location
`743001016` and reward location `743020036` are durable, and it does not alter
slot data or the canonical task-72 goal.

This fixture is disposable. Never reuse its native save or AP sidecar with a
normal task-72 seed, and never copy either artifact into a normal play setup.
