Feature: Verify Checksums
  As a researcher I want to ensure that all of the files being preserved are verified 
  as exact copies of the original files in my dataset.
  By providing checksums of my files, I can expect Archivematica to verify them
  during the transfer process.

Scenario: Checksums provided and verified
  # this scenario can be successfully executed using the following dataset
  # https://github.com/artefactual-labs/rdss-archivematica-test-data-corpus/blob/master/collection/10.5281/zenodo.46430/SIPmetadata/SIP-1.request.json
  
  Given checksum metadata is included in a preservation request
  	# i.e. for now this means included in metadata create json message
  
  When the preservation request is sent to archivematica_channel_adaptor
    # i.e. message sent using msgCreator to trigger automated workflow
  
  Then a new transfer is created and approved in the dashboard
  And a the checksum metadata is included in files in the transfers metadata directory
  And the Verify Transfer Checksums  microservice is run
  And the job Verify metadata directory checksums reports "Completed Successfully"
    
Scenario: Invalid checksum provided 
  # no dataset & message has been uploaded to github repo yet
  # to execute this test, use example above but manually change the checksum value in msgCreator
  
  Given checksum metadata is included in a preservation request
  	# i.e. for now this means included in metadata create json message
  
  When the preservation request is sent to archivematica_channel_adaptor
    # i.e. message sent using msgCreator to trigger automated workflow
  
  Then a new transfer is created and approved in the dashboard
  And a the checksum metadata is included in files in the transfers metadata directory
  And the microservice "Verify Transfer Checksums" is run
  And the job "Verify metadata directory checksums" reports "Failed"
  And the microservice "Failed Transfer" is run
  And the job "Move the failed directory" reports "Completed Successfully"
	# currently the job "Email Fail Report" fails because email server is not configured

# to do
#	Scenario: No checksums provided
#   do we need to update documentation about how the checksum files are created? 
