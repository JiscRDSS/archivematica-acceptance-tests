# Jisc RDSS Acceptance Tests

This directory holds Gherkin Acceptance Tests for the JISC RDSS project. 

A description of the acceptance tests we intend to develop for the project can
be found on the project wiki: [Candidate Feature (Gherkin) Set for Automated Workflow] (https://jiscdev.atlassian.net/wiki/display/RDSSAR/Candidate+Feature+%28Gherkin%29+Set+for+Automated+Workflow)

For an overview of the entire repo, see the main [readme file for the repo] (https://github.com/JiscRDSS/archivematica-acceptance-tests/blob/dev/issue-11064-remove-project-specifics/README.rst). 
(Note that this link currently points to the readme of the Dev branch -- merging this
into the Master branch is wip due to some minor blocking issues in the public repo)

## Collaboration and Worfklow for the RDSS Arkivum project team
Acceptance Tests (aka feature files) that are in development should be included in 
this directory within a 'dev - new features' branch. 

To make updates to a test, create a branch with your name and the name of the test
(e.g. peterVG - register-preservation-request). Commit your changes and then make a 
pull request to merge those changes into the 'dev - new features' branch.

When the acceptance tests can be executed and pass, they should be merged into the 
Master branch. 

## Community Engagement with the public project
Acceptance tests that rely on Jisc specific integration, configuration, test data
etc. should not be merged with the public Archivematica-Acceptance-Test repo.  

Acceptance tests that test functionality in the core Archivematica system (even if
it is new functionality created for Jisc) should be merged with the public 
Archivematica-Acceptance-Test repo. This allows us to contribute back to the 
community and be part of a community effort to build out acceptance tests for 
the entire system.  

To that end, we should aim to keep Jisc dependencies confined to certain tests, 
and make general functionality tests as independent of them as possible (this is 
explained somewhat in the wiki link above where we describre 'new features' 
vs. 'regression tests'
