# SSMS and Agentic Migration Video Transcription

Source recording: `ssmsandagenticmigration.mp4` (stored outside this repository)

Duration: 2:09.1

## Timestamped Transcript

**00:00-00:05** I'm starting in the new SSMS migration experience, which takes me in to in through the migration process.

**00:06-00:11** Now, I've already run this assessment, and the completed assessment recommends Azure SQL Database Hyperscale.

**00:12-00:15** It also identifies a few compatibility items to address before moving.

**00:16-00:18** Now, this is the application we're migrating.

**00:19-00:24** It manages orders, fulfillment, inventory, and, of course, the operational dashboard.

**00:24-00:28** The goal is to move the application and database without changing how they work.

**00:28-00:30** So let's switch to VS Code.

**00:30-00:36** I've given GitHub Copilot a prompt describing the application, database, and the desired outcome.

**00:36-00:45** Copilot's going to use those new SQL migration skills, in addition to other things, of course, to guide the assessment, remediation, migration, and validation.

**00:46-00:52** I'll save you the back and forth while Copilot investigates and resolves the issues and takes me through the migration process.

**00:52-00:54** But here's the completed result.

**00:54-00:57** Copilot validates its changes and confirms everything's healthy.

**00:58-01:00** Now, let's return to that application.

**01:01-01:05** It has moved from my local environment to Azure, but the user experience hasn't changed.

**01:05-01:13** The same dashboard, orders, fulfillment, inventory, and partner experiences work, and I can still create orders.

**01:14-01:16** So how did we get here?

**01:16-01:20** Of course, these skills, and this is just a selection, helped a bunch.

**01:20-01:28** But Copilot's final summary shows the application assessment and remediation, followed by the SQL Server 2016 database assessment.

**01:29-01:34** It found the same compatibility issues surfaced in SSMS, which is what you would expect.

**01:34-01:37** And then it went through the process of remediating the database.

**01:37-01:43** It also explains the hyperscale recommendation and choice that was ultimately made.

**01:43-01:48** A fully managed, license-included target that avoids a separate SQL Server license purchase.

**01:49-01:50** It's at the price of open source.

**01:51-01:59** Then it documents how it went through the data migration, restoring the application health, and once again validates the results with a test transaction.

**02:00-02:03** SSMS gives us a great trusted migration entry point.

**02:03-02:09** Copilot and migration skills help carry the work, whether it's one-to-one or at scale.