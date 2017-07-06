@download-AIP @JiscRDSS

Feature: Trigger and confirm automated workflow has created an AIP
  As a Data Manager, I want to preserve some datasets with as little intervention
  as possible, so that I can ensure some level of preservation is 
  carried even when I do not have time for hands-on preservation work. 
 
  This feature is a simple regression test to check that when we trigger the
  automated using a well-formed message the dataset is preserved and stored in an AIP. 
 
Scenario:  
 Given that my "Cities" dataset has been published on the RDSS platform
 And a MetadataCreate message has been generated for my dataset 
 	# these steps have been done and wouldn't need to be tested 
 	
 When I copy the MetadataCreate message into the msgCreator application
   # e.g. https://github.com/artefactual-labs/rdss-archivematica-test-data-corpus/blob/master/collection/10.5281/zenodo.46430/SIPmetadata/SIP-1.request.json
 and click "send" 
 
 Then my dataset is transferred to Archivematica for automated processing
 And I log into Archivematica
 And select the "Archival Storage" tab
 And select the "Cities" AIP
 And I can download the AIP
 
# this doesn't attempt to validate what is in the AIP etc; but it would 
# confirm that the dataset was transferred and processing completed
 
