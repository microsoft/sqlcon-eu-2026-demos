# SSMS Migration and Agentic Modernization Demo

> Delivery track for the 2-minute, 9-second recording. It follows the recorded workflow:
> SSMS assessment, application baseline, Copilot-guided remediation and migration, and
> post-migration validation.

## Timing and Actions

| Time | On-screen action | Story beat |
| --- | --- | --- |
| 0:00-0:15 | Show the completed SSMS assessment and Hyperscale recommendation. | SSMS starts the migration journey and identifies compatibility work. |
| 0:16-0:28 | Show the local application and move across its dashboard, orders, fulfillment, and inventory. | Establish the application that must keep working. |
| 0:28-0:57 | Move to VS Code. Show the modernization prompt, then jump to the completed Copilot validation. | Copilot and SQL migration skills guide the assessment, remediation, migration, and validation. |
| 0:58-1:13 | Open the migrated Azure application and switch among its experiences. | Prove that the application behavior is unchanged after migration. |
| 1:14-1:59 | Return to Copilot and scroll through its final summary. | Explain the assessment, remediation, Hyperscale choice, migration, restored health, and test transaction. |
| 2:00-2:09 | Hold on the final validation or application. | Close on the combined SSMS and agentic migration story. |

## Talk Track

I'm starting in the new SSMS migration experience, which takes me through the migration process.

Now, I've already run this assessment, and the completed assessment recommends Azure SQL Database Hyperscale.

It also identifies a few compatibility items to address before moving.

Now, this is the application we're migrating.

It manages orders, fulfillment, inventory, and, of course, the operational dashboard.

The goal is to move the application and database without changing how they work.

So let's switch to VS Code.

I've given GitHub Copilot a prompt describing the application, database, and the desired outcome.

Copilot's going to use those new SQL migration skills, in addition to other things, of course, to guide the assessment, remediation, migration, and validation.

I'll save you the back and forth while Copilot investigates and resolves the issues and takes me through the migration process.

But here's the completed result.

Copilot validates its changes and confirms everything's healthy.

Now, let's return to that application.

It has moved from my local environment to Azure, but the user experience hasn't changed.

The same dashboard, orders, fulfillment, inventory, and partner experiences work, and I can still create orders.

So how did we get here?

Of course, these skills, and this is just a selection, helped a bunch.

But Copilot's final summary shows the application assessment and remediation, followed by the SQL Server 2016 database assessment.

It found the same compatibility issues surfaced in SSMS, which is what you would expect.

And then it went through the process of remediating the database.

It also explains the hyperscale recommendation and choice that was ultimately made.

A fully managed, license-included target that avoids a separate SQL Server license purchase.

It's at the price of open source.

Then it documents how it went through the data migration, restoring the application health, and once again validates the results with a test transaction.

SSMS gives us a great trusted migration entry point.

Copilot and migration skills help carry the work, whether it's one-to-one or at scale.

## Delivery Notes

- Source recording: `ssmsandagenticmigration.mp4`.
- Recorded duration: 2:09.1.
- The timestamped source transcript is retained in `transcription.md`; this delivery track
	removes transcription false starts only.
- Follow the recording's visual timing; it leaves approximately 11 seconds before the 2:20 limit.