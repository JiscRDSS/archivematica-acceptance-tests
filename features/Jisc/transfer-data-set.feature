Feature: Transfer Data Set:
  The preservation system needs to copy the dataset to a storage location where it can 
  carry out preservation processing (in order to ensure that access or updates from RDSS
  users do not interfere with preservation processing). 

Scenario: Successful DataSet Transfer
  Given archivematica_channel_adaptor has received a valid Preservation Request
	# as described by register-preservation-request.feature	
  
  When archivematica_channel_adaptor creates a temporary directory inside the standardTransfer directory
    # in the archivematica_transfer_deposit_dir (as per root.go)
  And archivematica_channel_adaptor copies each file to the temporary directory

  Then archivematica watches the standardTransfer directory for new sub-directories
  And archivematica_channel_adaptor checks for the new (i.e. unnaproved) transfer 
    # as per /api/transfer/unapproved described by https://wiki.archivematica.org/Archivematica_API
  And archivematica_channel_adaptor approves the new transfer 
    # as per /api/transfer/approve described by https://wiki.archivematica.org/Archivematica_API
  And archivematica starts to process the transfer using the "automated" processing configuration

# to-do items (for backlog)
#	a) validation that all files were transferred from S3
#	b) validation that all files transferred from s3 are the same (i.e. fixity check? or is this not necesseary because AM will do it anyway?)
#	c) any other validation?
#	d) recreating folder hierachy? currently S3 datasets are flat... 
#	e) changes need to be made to Archivematica API so that we don't need to use a watched folder (current AM API has
#	   dependency on storage service UUIDs...)   
