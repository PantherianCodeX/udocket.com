Switching tools in case is very slow - it used to be very quick - re-optimize
Remove UUID prefix from all filenames and ensure that UUID's are only used internally and in diagnostic data, not to the general user. Don't worry about permissions, leave diagnostic UUID display but use friendly UUID display with typehints via a template or something to make anything with a UUID friendly when it is necessary to display it. Keep full UUID in logs and othe diag data. For example, the downloads should all be renamed to omit the UUID and displays 

Case Details Page

Analyze 
Job details do not have the ability to download the files - it should have the same download button menu as the lastest analyze results
Latest analyze result
- should be more compact without boxes around everything.
- Remove Providers field - replace with model


Team Alerts:
- not updating transcript reviews count. I only have 2 transcripts, both are approved and it says 3 are awaiting approval.


Common pipeline progress:
Analyze job: progress addition wasn't done correctly
- It is in the setup and run card. This should be an expandable panel in the job details pane so it only shows when you open it
- Completely move pipeline progress to common code and/or template and implement in both Analyze and Compose
- Job details should be opened when a job is started so they can monitor progress or move on at will.
- When job finished, replace it with the normal details
- Job Status sometimes says compose.progress instead of the actual progress and doesn't update until refresh.
- Use logs to get a baseline of time per 

Compose logs are bad - it's hard to see what's going on. Enhance and bring it up to high standards, like other programs.



Roadmap Item:
Refactor of Jobs functionality:
- Right now we have the parent job task in the list, and sub-tasks can be added manually or automatically like Manual Edit (manual) and Audio Conversion (automatic).
- We now want the parent job to hold the end results of the processing when available.
- When a task starts, it must create a sub-task for whatever operations are being done. (e.g. Transcribe Job Start => Audio Conversion > Transcribe
- We should have a generic shared job manager that coordinates task creations and modifications, since making changes mid-tasklist requires regenerating the other subtasks and merging manual edits and whatnot
